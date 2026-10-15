import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.db.session import get_engine, get_session_factory
from app.models import (
    DataSource,
    FundamentalFact,
    Instrument,
    Prediction,
    PriceDailyVersion,
    RawIngestion,
    User,
)
from app.schemas.assistant import TimeMachineInput
from app.services.auth import AuthService
from app.services.raw_ingestion import RawIngestionService
from app.services.time_machine import TimeMachineService


@pytest.mark.integration
def test_actual_archive_late_import_restatement_later_prediction_and_missing_raw():
    async def run():
        uid, iid, sid = uuid4(), uuid4(), uuid4()
        raws = []
        async with get_session_factory()() as db:
            try:
                user = await AuthService(db).create_user(
                    "p10_" + uuid4().hex[:12], secrets.token_urlsafe(32)
                )
                uid = user.id
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC PIT TEST",
                        ticker="P10" + uuid4().hex[:8],
                        currency="CHF",
                        asset_type="STOCK",
                    )
                )
                source = DataSource(
                    id=sid,
                    name="SYNTHETIC archive test",
                    slug="TEST_P10_" + uuid4().hex.upper(),
                    type="MANUAL",
                    trust_level="C",
                    enabled=False,
                    gate_status="UNKNOWN",
                )
                db.add(source)
                await db.commit()
                service = RawIngestionService(db)
                first = await service.store(
                    data=b"SYNTHETIC first price and fundamental version",
                    source_id=sid,
                    source_slug=source.slug,
                    resource_type="TEST_P10_ARCHIVE",
                )
                raws.append(first.id)
                then = datetime.now(UTC)
                period = then.date() - timedelta(days=30)
                price = PriceDailyVersion(
                    id=uuid4(),
                    instrument_id=iid,
                    trading_date=period,
                    close=100,
                    currency="CHF",
                    source_id=sid,
                    raw_ingestion_id=first.id,
                    row_number=1,
                    observed_at=then,
                    known_at=then,
                    retrieved_at=then,
                    created_at=then,
                    validation_status="VALID",
                    parser_version="TEST",
                    validation_version="TEST",
                    reconciliation_version="TEST",
                    quality_score=1,
                    quality_label="HIGH",
                    quality_components={},
                    warnings=[],
                    resolution="ACCEPTED",
                )
                fact = FundamentalFact(
                    id=uuid4(),
                    instrument_id=iid,
                    metric="revenue",
                    value=100,
                    unit="CHF",
                    currency="CHF",
                    period_end=period,
                    period_type="ANNUAL",
                    row_key="first",
                    source_id=sid,
                    raw_ingestion_id=first.id,
                    known_at=then,
                    observed_at=then,
                    retrieved_at=then,
                    created_at=then,
                    validation_status="VALID",
                    parser_version="TEST",
                    rule_version="TEST",
                )
                db.add_all([price, fact])
                await db.commit()
                cutoff = datetime.now(UTC)
                # New local observations are genuinely later; only public period/date is old.
                second = await service.store(
                    data=b"SYNTHETIC later correction",
                    source_id=sid,
                    source_slug=source.slug,
                    resource_type="TEST_P10_ARCHIVE",
                )
                raws.append(second.id)
                later = datetime.now(UTC)
                correction = FundamentalFact(
                    id=uuid4(),
                    instrument_id=iid,
                    metric="revenue",
                    value=90,
                    unit="CHF",
                    currency="CHF",
                    period_end=period,
                    period_type="ANNUAL",
                    row_key="correction",
                    source_id=sid,
                    raw_ingestion_id=second.id,
                    known_at=then,
                    observed_at=later,
                    retrieved_at=later,
                    created_at=later,
                    validation_status="VALID",
                    parser_version="TEST",
                    rule_version="TEST",
                    replaces_version_id=fact.id,
                )
                forecast = Prediction(
                    user_id=uid,
                    instrument_id=iid,
                    horizon=30,
                    generated_at=later,
                    information_cutoff_at=then,
                    created_at=later,
                    result={
                        "confidence_status": "NO RELIABLE FORECAST",
                        "model_versions": [],
                        "notice": "SYNTHETIC TEST abstention",
                    },
                )
                db.add_all([correction, forecast])
                await db.commit()
                machine = TimeMachineService(db, uid)
                strict = await machine.inspect(TimeMachineInput(instrument_id=iid, as_of=cutoff))
                assert Decimal(str(strict["sections"]["fundamentals"]["items"][0]["value"])) == 100
                assert strict["sections"]["predictions"]["status"] == "NO HISTORICAL PREDICTION"
                reconstructed = await machine.inspect(
                    TimeMachineInput(
                        instrument_id=iid, as_of=cutoff, mode="RECONSTRUCTED_HISTORICAL"
                    )
                )
                assert (
                    reconstructed["sections"]["predictions"]["status"] == "NO HISTORICAL PREDICTION"
                )
                assert (
                    Decimal(
                        str(
                            reconstructed["reconstruction_separate"]["fundamentals"]["items"][0][
                                "value"
                            ]
                        )
                    )
                    == 90
                )
                current = await machine.inspect(
                    TimeMachineInput(instrument_id=iid, as_of=datetime.now(UTC))
                )
                assert [r["id"] for r in current["sections"]["fundamentals"]["items"]] == [
                    correction.id
                ]

                # Original absence is not silently replaced with today's correction.
                class MissingRaw:
                    async def get_verified(self, identifier):
                        from app.core.errors import AppError

                        raise AppError(503, "RAW_STORAGE_UNAVAILABLE", "Synthetic outage")

                import app.services.time_machine as module

                original = module.RawIngestionService
                module.RawIngestionService = lambda db: MissingRaw()
                try:
                    unavailable = await machine.inspect(
                        TimeMachineInput(instrument_id=iid, as_of=cutoff)
                    )
                    assert unavailable["sections"]["prices"]["items"] == []
                    assert unavailable["sections"]["prices"]["unavailable"]
                finally:
                    module.RawIngestionService = original
            finally:
                await db.rollback()
                for model in (Prediction, FundamentalFact, PriceDailyVersion):
                    await db.execute(delete(model).where(model.instrument_id == iid))
                await db.execute(delete(Instrument).where(Instrument.id == iid))
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raws)))
                await db.execute(delete(DataSource).where(DataSource.id == sid))
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
