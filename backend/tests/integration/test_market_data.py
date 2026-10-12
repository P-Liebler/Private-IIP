from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, or_

from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.models import (
    AuditEvent,
    CorporateAction,
    CorporateActionVersion,
    DataQuarantine,
    FxRate,
    FxRateVersion,
    Instrument,
    InstrumentIdentifier,
    PriceDaily,
    PriceDailyVersion,
    RawIngestion,
)
from app.providers.ecb_fx import EcbFxCollector
from app.providers.snb_fx import SnbFxCollector
from app.services.market_import import MarketImportService
from app.services.market_queries import MarketQueryService, total_return
from app.services.market_validation import discrepancy, validate_price
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, _content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.mark.integration
def test_p3_manual_import_versions_pit_fx_actions_and_quarantine() -> None:
    async def run() -> None:
        storage = MemoryStorage()
        instrument_id = uuid4()
        ticker = "T" + uuid4().hex[:10].upper()
        raw_ids = []
        async with get_session_factory()() as db:
            fx_day = date(1800, 1, 2)
            existing_fx = [await db.get(FxRate, (base, "CHF", fx_day)) for base in ("USD", "EUR")]
            if any(item is not None for item in existing_fx):
                pytest.skip("Synthetic FX test date is already populated")
            instrument = Instrument(
                id=instrument_id,
                name="Synthetic P3 Test",
                asset_type="STOCK",
                currency="USD",
                ticker=ticker,
            )
            db.add(instrument)
            db.add(
                InstrumentIdentifier(
                    instrument_id=instrument_id,
                    type="TICKER",
                    value=ticker,
                    market_key="",
                    valid_from=date(2020, 1, 1),
                    observed_at=datetime.now(UTC),
                )
            )
            await db.commit()
            service = MarketImportService(db, RawIngestionService(db, storage))
            query = MarketQueryService(db)
            try:
                source = await SourceService(db).get("SNB")
                if source.gate_status == "UNKNOWN":
                    with pytest.raises(AppError) as blocked:
                        SourceGate.require_enabled(source, "fx_rates")
                    assert blocked.value.code == "SOURCE_NOT_APPROVED"

                first_csv = (
                    "date,ticker,open,high,low,close,volume,currency\n"
                    f"2024-01-02,{ticker},100,105,95,100,1000,USD\n"
                    f"2024-01-03,{ticker},50,53,48,50,900,USD\n"
                ).encode()
                preview = await service.preview("prices", first_csv, "prices.csv")
                raw_ids.append(preview["raw_ingestion_id"])
                assert preview["row_count"] == 2 and preview["invalid_count"] == 0
                before_commit = await query.prices(
                    instrument_id, date(2024, 1, 2), date(2024, 1, 3)
                )
                assert before_commit["status"] == "UNAVAILABLE"
                assert before_commit["prices"] == []
                mapping = preview["mapping"]
                committed = await service.commit("prices", preview["raw_ingestion_id"], mapping)
                assert committed["inserted"] == 2
                assert (await service.commit("prices", preview["raw_ingestion_id"], mapping))[
                    "unchanged"
                ] == 2
                cutoff = datetime.now(UTC)
                prices = (await query.prices(instrument_id, date(2024, 1, 2), date(2024, 1, 3)))[
                    "prices"
                ]
                assert len(prices) == 2 and prices[0]["close"] == Decimal("100")
                parts = prices[0]["quality_components"]
                expected_score = round(
                    parts["source_trust"] * 0.40
                    + parts["cross_validation"] * 0.25
                    + parts["freshness"] * 0.15
                    + parts["schema_quality"] * 0.10
                    + parts["historical_consistency"] * 0.10,
                    4,
                )
                assert prices[0]["quality_score"] == expected_score

                corrected = await service.preview(
                    "prices",
                    f"date,ticker,close,currency\n2024-01-02,{ticker},101,USD\n".encode(),
                    "correction.csv",
                )
                raw_ids.append(corrected["raw_ingestion_id"])
                with pytest.raises(AppError) as conflict:
                    await service.commit(
                        "prices", corrected["raw_ingestion_id"], corrected["mapping"]
                    )
                assert conflict.value.code == "PRICE_CONFLICT_REVIEW"
                applied = await service.commit(
                    "prices",
                    corrected["raw_ingestion_id"],
                    corrected["mapping"],
                    conflict_policy="ACCEPT_NEW",
                    decision_note="Synthetic correction verified",
                )
                assert applied["corrected"] == 1
                old = (
                    await query.prices(instrument_id, date(2024, 1, 2), date(2024, 1, 2), cutoff)
                )["prices"]
                new = (await query.prices(instrument_id, date(2024, 1, 2), date(2024, 1, 2)))[
                    "prices"
                ]
                assert old[0]["close"] == Decimal("100") and new[0]["close"] == Decimal("101")
                assert new[0]["replaces_version_id"] == old[0]["id"]
                assert len(await query.price_versions(instrument_id, date(2024, 1, 2))) == 2

                invalid = await service.preview(
                    "prices",
                    f"date,ticker,close,currency\n2024-01-04,{ticker},-2,USD\n2024-01-05,{ticker},51,USD\n".encode(),
                    "mixed.csv",
                )
                raw_ids.append(invalid["raw_ingestion_id"])
                assert invalid["invalid_count"] == 1
                with pytest.raises(AppError) as partial:
                    await service.commit("prices", invalid["raw_ingestion_id"], invalid["mapping"])
                assert partial.value.code == "ROWS_INVALID"
                result = await service.commit(
                    "prices", invalid["raw_ingestion_id"], invalid["mapping"], accept_partial=True
                )
                assert result["quarantined"] == 1 and result["inserted"] == 1

                actions = await service.preview(
                    "actions",
                    f"date,ticker,action_type,value,currency,new_ticker\n2024-01-03,{ticker},SPLIT,2,,\n".encode(),
                    "actions.csv",
                )
                raw_ids.append(actions["raw_ingestion_id"])
                assert actions["invalid_count"] == 0
                await service.commit("actions", actions["raw_ingestion_id"], actions["mapping"])
                known_actions = (
                    await query.actions(instrument_id, date(2024, 1, 2), date(2024, 1, 3))
                )["actions"]
                assert known_actions[0]["type"] == "SPLIT"
                assert total_return(Decimal("100"), Decimal("50"), known_actions) == 0

                fx = await service.preview(
                    "fx",
                    f"date,base_currency,quote_currency,rate\n{fx_day},USD,CHF,0.9\n{fx_day},EUR,CHF,1.1\n".encode(),
                    "fx.csv",
                )
                raw_ids.append(fx["raw_ingestion_id"])
                assert fx["invalid_count"] == 0
                await service.commit("fx", fx["raw_ingestion_id"], fx["mapping"])
                direct = await query.fx("USD", "CHF", fx_day + timedelta(days=1))
                inverse = await query.fx("CHF", "USD", fx_day + timedelta(days=1))
                cross = await query.fx("USD", "EUR", fx_day + timedelta(days=1))
                assert direct["rate"] == Decimal("0.9") and direct["carry_days"] == 1
                assert inverse["rate"] == Decimal(1) / Decimal("0.9")
                assert cross["rate"] == Decimal("0.9") / Decimal("1.1")
                assert (await query.fx("USD", "CHF", fx_day + timedelta(days=7)))[
                    "status"
                ] == "UNAVAILABLE"
                assert (await query.quality_summary())["quarantined_rows"] >= 1
            finally:
                await db.rollback()
                await db.execute(
                    delete(PriceDaily).where(PriceDaily.instrument_id == instrument_id)
                )
                await db.execute(
                    delete(CorporateAction).where(CorporateAction.instrument_id == instrument_id)
                )
                await db.execute(
                    delete(FxRate).where(
                        FxRate.base_currency.in_(["USD", "EUR"]),
                        FxRate.quote_currency == "CHF",
                        FxRate.rate_date == fx_day,
                    )
                )
                await db.execute(
                    delete(PriceDailyVersion).where(
                        PriceDailyVersion.instrument_id == instrument_id
                    )
                )
                await db.execute(
                    delete(CorporateActionVersion).where(
                        CorporateActionVersion.instrument_id == instrument_id
                    )
                )
                await db.execute(
                    delete(FxRateVersion).where(FxRateVersion.raw_ingestion_id.in_(raw_ids))
                )
                await db.execute(
                    delete(DataQuarantine).where(DataQuarantine.raw_ingestion_id.in_(raw_ids))
                )
                raw_id_strings = [str(item) for item in raw_ids]
                await db.execute(
                    delete(AuditEvent).where(
                        or_(
                            AuditEvent.resource_id.in_(raw_id_strings),
                            AuditEvent.metadata_json["raw_ingestion_id"].astext.in_(raw_id_strings),
                        )
                    )
                )
                await db.execute(
                    delete(InstrumentIdentifier).where(
                        InstrumentIdentifier.instrument_id == instrument_id
                    )
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raw_ids)))
                await db.execute(delete(Instrument).where(Instrument.id == instrument_id))
                await db.commit()
        await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_unknown_fx_sources_and_blocked_yahoo_make_no_http_request() -> None:
    async def run() -> None:
        calls: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, text="unexpected")

        async with get_session_factory()() as db:
            ecb = await SourceService(db).get("ECB")
            snb = await SourceService(db).get("SNB")
            yahoo = await SourceService(db).get("YAHOO")
            if ecb.gate_status != "UNKNOWN" or snb.gate_status != "UNKNOWN":
                pytest.skip("An operator has already reviewed an FX source")
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                with pytest.raises(AppError) as denied:
                    await EcbFxCollector(db, client=client).collect(
                        date(2024, 1, 2), date(2024, 1, 3)
                    )
                assert denied.value.code == "SOURCE_NOT_APPROVED"
                with pytest.raises(AppError) as denied:
                    await SnbFxCollector(db).collect(date(2024, 1, 2), date(2024, 1, 3))
                assert denied.value.code == "SOURCE_NOT_APPROVED"
            assert yahoo.gate_status == "BLOCKED" and not yahoo.enabled
            assert calls == []
        await get_engine().dispose()

    asyncio.run(run())


def test_price_validation_and_threshold_boundaries() -> None:
    with pytest.raises(ValueError, match="High"):
        validate_price({"date": "2024-01-02", "close": "105", "high": "100"}, "USD")
    with pytest.raises(ValueError, match="währung"):
        validate_price({"date": "2024-01-02", "close": "100", "currency": "EUR"}, "USD")

    def at_percent(pct: str) -> Decimal:
        change = Decimal(pct)
        value = Decimal(100) * (Decimal(200) + change) / (Decimal(200) - change)
        return value.quantize(Decimal("0.00000001"), rounding=ROUND_CEILING)

    assert discrepancy(Decimal(100), at_percent("0.24"))[0] == "CONSISTENT"
    assert discrepancy(Decimal(100), at_percent("0.25"))[0] == "NOTICE"
    assert discrepancy(Decimal(100), at_percent("0.49"))[0] == "NOTICE"
    assert discrepancy(Decimal(100), at_percent("0.50"))[0] == "REVIEW"
    assert discrepancy(Decimal(100), at_percent("1.99"))[0] == "REVIEW"
    assert discrepancy(Decimal(100), at_percent("2.01"))[0] == "SEVERE"
