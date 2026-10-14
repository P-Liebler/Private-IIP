"""Explicit local SYNTHETIC P6 acceptance data with a simulated historical clock.

Never runs at startup. Refuses production and non-disposable users. These are
simulation timestamps, not evidence of a real historical archive.
"""

import asyncio
import json
import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import (
    ActionCoverageReview,
    AvailabilityReview,
    DataSource,
    Instrument,
    PriceDailyVersion,
    UniverseDefinition,
    UniverseMembershipVersion,
    User,
)
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.raw_ingestion import RawIngestionService


async def main() -> None:
    username = os.environ.get("E2E_USERNAME", "")
    if get_settings().app_env not in {"local", "test"} or not username.startswith("restore_"):
        raise RuntimeError("Explicit local disposable restore user required")
    async with get_session_factory()() as db:
        user = (await db.scalars(select(User).where(User.username == username))).one()
        suffix = uuid4().hex[:10]
        source = DataSource(
            name="SYNTHETIC P6 acceptance only",
            slug="TEST_P6_" + suffix.upper(),
            type="MANUAL",
            trust_level="D",
            priority=100,
            enabled=True,
            gate_status="APPROVED",
            allowed_uses=["synthetic_fixture"],
            checked_at=datetime.now(UTC),
            decision_by="explicit local acceptance",
            decision_note="Synthetic simulation; no external rights",
        )
        db.add(source)
        await db.commit()
        universe = UniverseDefinition(
            user_id=user.id,
            name="SYNTHETIC P6 Golden " + suffix,
            configuration={"kind": "CUSTOM_UNIVERSE", "synthetic": True},
        )
        negative = UniverseDefinition(
            user_id=user.id,
            name="SYNTHETIC P6 Unverified " + suffix,
            configuration={"kind": "CUSTOM_UNIVERSE", "synthetic": True},
        )
        stock = Instrument(
            name="SYNTHETIC P6 US " + suffix,
            asset_type="STOCK",
            ticker="P6US" + suffix,
            exchange="NYSE",
            currency="USD",
            country="US",
        )
        benchmark = Instrument(
            name="SYNTHETIC P6 ETF " + suffix,
            asset_type="ETF",
            ticker="P6ETF" + suffix,
            exchange="NYSE",
            currency="USD",
            country="US",
        )
        swiss = Instrument(
            name="SYNTHETIC P6 CH " + suffix,
            asset_type="STOCK",
            ticker="P6CH" + suffix,
            exchange="SIX",
            currency="CHF",
            country="CH",
        )
        euro = Instrument(
            name="SYNTHETIC P6 EUR " + suffix,
            asset_type="STOCK",
            ticker="P6EUR" + suffix,
            exchange="SIX",
            currency="EUR",
            country="CH",
        )
        db.add_all([universe, negative, stock, benchmark, swiss, euro])
        await db.commit()
        raw = await RawIngestionService(db).store(
            data=json.dumps(
                {
                    "SYNTHETIC": True,
                    "simulation": "complete declared two-member universe; no real archive",
                    "members": [str(stock.id), str(benchmark.id)],
                }
            ).encode(),
            source_id=source.id,
            source_slug=source.slug,
            resource_type="synthetic_p6",
            request_metadata={"user_id": str(user.id)},
        )
        historical = datetime(2023, 12, 1, tzinfo=UTC)
        membership = UniverseMembershipVersion(
            universe_id=universe.id,
            instrument_id=stock.id,
            valid_from=date(2023, 12, 1),
            valid_to=None,
            known_at=historical,
            observed_at=historical,
            source_id=source.id,
            raw_ingestion_id=raw.id,
            membership_status="LISTED",
            row_key=digest(stock.id),
            version="synthetic-v1",
            evidence={"SYNTHETIC": True},
        )
        unverified = UniverseMembershipVersion(
            universe_id=negative.id,
            instrument_id=stock.id,
            valid_from=date(2023, 12, 1),
            valid_to=None,
            known_at=historical,
            observed_at=datetime.now(UTC),
            source_id=source.id,
            raw_ingestion_id=raw.id,
            membership_status="LISTED",
            row_key=digest(stock.id),
            version="synthetic-asserted-v1",
            evidence={"level": "USER_ASSERTED", "SYNTHETIC": True},
        )
        db.add_all([membership, unverified])
        await db.flush()
        for kind, entity in [("membership", membership.id), ("universe", universe.id)]:
            db.add(
                AvailabilityReview(
                    entity_type=kind,
                    entity_id=entity,
                    raw_ingestion_id=raw.id,
                    reviewer_id=user.id,
                    level="VERIFIED_SOURCE_DOCUMENT",
                    rationale="Explicit synthetic simulation fixture, not real historical evidence",
                    evidence={
                        "SYNTHETIC": True,
                        "valid_from": "2023-12-01",
                        "valid_to": "2024-01-05",
                        "includes_delisted": True,
                    },
                    created_at=historical,
                )
            )
        await db.commit()
        calendar = MarketCalendarService()
        for index, day in enumerate(
            calendar.sessions_between("NYSE", date(2024, 1, 2), date(2024, 1, 5))
        ):
            receipt = calendar.session_close("NYSE", day) + timedelta(seconds=5)
            for instrument in (stock, benchmark):
                price_raw = await RawIngestionService(db).store(
                    data=json.dumps(
                        {
                            "SYNTHETIC": True,
                            "simulation_observed_at": receipt.isoformat(),
                            "instrument_id": str(instrument.id),
                            "open": "100",
                            "close": "110" if index == 3 else "100",
                        }
                    ).encode(),
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="synthetic_p6",
                    instrument_id=instrument.id,
                )
                price = PriceDailyVersion(
                    instrument_id=instrument.id,
                    trading_date=day,
                    open="100",
                    high="110",
                    low="100",
                    close="110" if index == 3 else "100",
                    volume="1000",
                    currency="USD",
                    source_id=source.id,
                    raw_ingestion_id=price_raw.id,
                    row_number=1,
                    observed_at=receipt,
                    known_at=receipt,
                    retrieved_at=receipt,
                    validation_status="VALID",
                    parser_version="synthetic-v1",
                    validation_version="synthetic-v1",
                    reconciliation_version="synthetic-v1",
                    quality_score=1,
                    quality_label="VERIFIED",
                    quality_components={},
                    warnings=["SYNTHETIC_SIMULATED_HISTORY"],
                    resolution="ACCEPTED",
                )
                db.add(price)
                await db.flush()
                db.add(
                    AvailabilityReview(
                        entity_type="price",
                        entity_id=price.id,
                        raw_ingestion_id=price_raw.id,
                        reviewer_id=user.id,
                        level="LOCAL_FIRST_OBSERVATION",
                        rationale=(
                            "Synthetic historical-clock fixture; not a real historical archive"
                        ),
                        evidence={"SYNTHETIC": True},
                        created_at=receipt,
                    )
                )
                db.add(
                    ActionCoverageReview(
                        instrument_id=instrument.id,
                        start_date=date(2022, 1, 1),
                        end_date=day,
                        source_id=source.id,
                        raw_ingestion_id=price_raw.id,
                        reviewer_id=user.id,
                        action_version_ids=[],
                        rationale=(
                            "Synthetic fixture explicitly declares no actions "
                            "through simulated date"
                        ),
                        created_at=receipt,
                    )
                )
                await db.commit()
        print(
            json.dumps(
                {
                    "universe_id": str(universe.id),
                    "universe_name": universe.name,
                    "unverified_universe_id": str(negative.id),
                    "benchmark_id": str(benchmark.id),
                    "instrument_id": str(stock.id),
                    "source_id": str(source.id),
                    "raw_id": str(raw.id),
                    "start": "2024-01-02",
                    "end": "2024-01-05",
                    "currency": "USD",
                    "expected_value": "1098.90",
                    "SYNTHETIC": True,
                }
            )
        )
    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
