"""Explicit synthetic local browser acceptance fixture; never application startup."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models import DataSource, Instrument, User
from app.schemas.research import FactInput
from app.services.fundamentals import FundamentalService
from app.services.raw_ingestion import RawIngestionService
from app.services.research import ResearchService


async def main() -> None:
    if get_settings().app_env not in {"local", "test"}:
        raise RuntimeError("Synthetic fixtures are local/test only")
    username = os.environ["E2E_USERNAME"]
    if not username.startswith("restore_"):
        raise RuntimeError("Use an explicitly created disposable restore-test user")
    async with get_session_factory()() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            raise RuntimeError("Test user missing")
        instrument = await db.get(Instrument, os.environ["E2E_RESEARCH_INSTRUMENT_ID"])
        if instrument is None or instrument.name != "Disposable restore test instrument":
            raise RuntimeError("Explicit restore fixture instrument required")
        instrument.country = "US"
        source = DataSource(
            id=uuid4(),
            slug=f"TEST_RESEARCH_{uuid4().hex}",
            name="Explicit synthetic P5 fixture",
            type="MANUAL",
            trust_level="D",
            priority=10,
            gate_status="APPROVED",
            enabled=True,
            checked_at=datetime.now(UTC),
            scope="Explicit synthetic local acceptance fixtures only",
            allowed_uses=["fundamentals"],
            decision_by="local-test-fixture",
            decision_note="No real company or external access",
            failure_count=0,
        )
        missing = Instrument(
            id=uuid4(),
            name="P5 Synthetic Missing Fundamentals",
            asset_type="STOCK",
            currency="CHF",
            country="CH",
        )
        db.add_all([source, missing])
        await db.commit()
        facts = []
        for year, revenue in [(2022, 700), (2023, 800), (2024, 900), (2025, 1000)]:
            for metric, value, unit in [
                ("revenue", revenue, "MONEY"),
                ("net_income", revenue // 10, "MONEY"),
                ("free_cash_flow", revenue // 10, "MONEY"),
                ("eps_diluted", revenue / 100, "PER_SHARE"),
            ]:
                facts.append(
                    FactInput(
                        instrument_id=instrument.id,
                        metric=metric,
                        value=str(value),
                        unit=unit,
                        currency="USD",
                        period_start=date(year, 1, 1),
                        period_end=date(year, 12, 31),
                        period_type="ANNUAL",
                        filing_reference="SYNTHETIC-BROWSER-REPORT",
                    )
                )
        instant = {
            "cash": "100",
            "total_assets": "800",
            "total_debt": "200",
            "total_equity": "400",
            "preferred_equity": "0",
            "minority_interest": "0",
            "shares_outstanding": "10",
        }
        for metric, value in instant.items():
            facts.append(
                FactInput(
                    instrument_id=instrument.id,
                    metric=metric,
                    value=value,
                    unit="SHARES" if metric == "shares_outstanding" else "MONEY",
                    currency=None if metric == "shares_outstanding" else "USD",
                    period_end=date(2025, 12, 31),
                    period_type="INSTANT",
                    filing_reference="SYNTHETIC-BROWSER-REPORT",
                    share_class=str(instrument.id) if metric == "shares_outstanding" else None,
                    split_basis_date=datetime.now(UTC).date()
                    if metric == "shares_outstanding"
                    else None,
                )
            )
        for metric, value in {
            "operating_income": "150",
            "gross_profit": "400",
            "operating_cash_flow": "150",
            "capex": "50",
            "income_tax": "20",
            "pretax_income": "100",
            "ebitda": "150",
        }.items():
            facts.append(
                FactInput(
                    instrument_id=instrument.id,
                    metric=metric,
                    value=value,
                    unit="MONEY",
                    currency="USD",
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    period_type="ANNUAL",
                    filing_reference="SYNTHETIC-BROWSER-REPORT",
                )
            )
        data = json.dumps(
            {
                "fixture_notice": "SYNTHETIC TEST DATA — no real company",
                "facts": [f.model_dump(mode="json") for f in facts],
            }
        ).encode()
        raw = await RawIngestionService(db).store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="synthetic_research_fixture",
            instrument_id=instrument.id,
            content_type="application/json",
        )
        await FundamentalService(db).persist(facts, raw, parser="synthetic-browser-v1")
        await db.commit()
        snapshot = await ResearchService(db).materialize(instrument.id)
        assert snapshot.result["scores"]["Quality"]["score"] is not None
        print(
            json.dumps(
                {
                    "instrument_id": str(instrument.id),
                    "missing_instrument_id": str(missing.id),
                    "source_id": str(source.id),
                    "raw_id": str(raw.id),
                    "snapshot_id": str(snapshot.id),
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
