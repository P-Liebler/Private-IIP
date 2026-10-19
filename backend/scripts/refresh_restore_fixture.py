"""Append dated synthetic acceptance observations; never refresh real holdings."""

import asyncio
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import DataSource, FundamentalFact, Instrument, User
from app.schemas.research import FactInput
from app.services.fundamentals import FundamentalService
from app.services.market_import import MarketImportService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService
from app.services.raw_ingestion import RawIngestionService


async def main() -> None:
    if (
        get_settings().app_env != "test"
        or os.environ.get("ALLOW_SYNTHETIC_FIXTURE_REFRESH") != "true"
    ):
        raise RuntimeError("Explicit local synthetic acceptance mode required")
    today = datetime.now(UTC).date()
    try:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == os.environ["E2E_USERNAME"]))
            assert user and user.username.startswith("restore_")
            portfolio_id = UUID(os.environ["E2E_PORTFOLIO_ID"])
            portfolio = await PortfolioService(db, user.id).owned(portfolio_id)
            instrument = await db.get(Instrument, UUID(os.environ["E2E_RESEARCH_INSTRUMENT_ID"]))
            assert portfolio.name == "Disposable restore test"
            assert instrument and instrument.name == "Disposable restore test instrument"
            assert instrument.currency == "USD" and instrument.ticker
            importer = MarketImportService(db)
            results = {}
            for kind, csv in (
                ("prices", f"date,ticker,close,currency\n{today},{instrument.ticker},120,USD\n"),
                ("fx", f"date,base_currency,quote_currency,rate\n{today},USD,CHF,0.9\n"),
            ):
                preview = await importer.preview(
                    kind, csv.encode(), f"SYNTHETIC-acceptance-{kind}.csv"
                )
                results[kind] = await importer.commit(
                    kind, preview["raw_ingestion_id"], preview["mapping"]
                )
            value = await PortfolioValuationService(db, user.id).value(portfolio_id, today)
            assert value["status"] == "COMPLETE" and value["total_value_base"] == Decimal("10180")
            shares = await db.scalar(
                select(FundamentalFact)
                .where(
                    FundamentalFact.instrument_id == instrument.id,
                    FundamentalFact.metric == "shares_outstanding",
                    FundamentalFact.validation_status != "REJECTED",
                )
                .order_by(FundamentalFact.observed_at.desc())
                .limit(1)
            )
            if shares and shares.evidence.get("split_basis_date") != today.isoformat():
                source = await db.get(DataSource, shares.source_id)
                assert source and source.slug.startswith("TEST_RESEARCH_")
                fact = FactInput(
                    instrument_id=instrument.id,
                    metric=shares.metric,
                    value=shares.value,
                    unit="SHARES",
                    period_end=shares.period_end,
                    period_type="INSTANT",
                    share_class=str(instrument.id),
                    split_basis_date=today,
                    filing_reference="SYNTHETIC-BROWSER-REPORT",
                )
                raw = await RawIngestionService(db).store(
                    data=json.dumps(
                        {
                            "fixture_notice": "SYNTHETIC TEST DATA; no real company",
                            "facts": [fact.model_dump(mode="json")],
                        }
                    ).encode(),
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="synthetic_research_fixture",
                    instrument_id=instrument.id,
                    content_type="application/json",
                )
                results["synthetic_share_basis"] = await FundamentalService(db).persist(
                    [fact], raw, parser="synthetic-browser-v1"
                )
                await db.commit()
            print(
                json.dumps(
                    {
                        "classification": "SYNTHETIC_ACCEPTANCE_ONLY_NOT_REAL_DATA",
                        "date": today.isoformat(),
                        "results": results,
                        "golden_value": str(value["total_value_base"]),
                    },
                    default=str,
                )
            )
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
