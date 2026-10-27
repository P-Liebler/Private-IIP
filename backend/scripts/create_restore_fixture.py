"""Create an explicit disposable local V1 fixture before a backup/restore test."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.db.session import get_session_factory
from app.models import Instrument, InstrumentIdentifier
from app.schemas.portfolio import AccountCreate, PortfolioCreate, TransactionInput
from app.services.auth import AuthService
from app.services.market_import import MarketImportService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService

TEST_PASSWORD = "test-only-restore-password-2"


async def main() -> None:
    from app.core.config import get_settings

    if get_settings().app_env == "production":
        raise RuntimeError("Synthetic restore fixtures are forbidden in production")
    today = datetime.now(UTC).date()
    username = "restore_" + uuid4().hex[:12]
    ticker = "R" + uuid4().hex[:10].upper()
    async with get_session_factory()() as db:
        user = await AuthService(db).create_user(username, TEST_PASSWORD)
        instrument = Instrument(
            id=uuid4(),
            name="Disposable restore test instrument",
            asset_type="STOCK",
            currency="USD",
            ticker=ticker,
        )
        db.add(instrument)
        db.add(
            InstrumentIdentifier(
                instrument_id=instrument.id,
                type="TICKER",
                value=ticker,
                market_key="",
                valid_from=today,
                observed_at=datetime.now(UTC),
            )
        )
        await db.commit()
        market = MarketImportService(db)
        price_csv = f"date,ticker,close,currency\n{today},{ticker},120,USD\n".encode()
        price_preview = await market.preview("prices", price_csv, "restore-price.csv")
        price_result = await market.commit(
            "prices", price_preview["raw_ingestion_id"], price_preview["mapping"]
        )
        assert price_result["inserted"] == 1
        fx_csv = f"date,base_currency,quote_currency,rate\n{today},USD,CHF,0.9\n".encode()
        fx_preview = await market.preview("fx", fx_csv, "restore-fx.csv")
        fx_result = await market.commit("fx", fx_preview["raw_ingestion_id"], fx_preview["mapping"])
        # Re-running a synthetic fixture on the same UTC day may reuse the exact
        # already archived FX row. A duplicate is valid; corrections are not.
        assert fx_result["inserted"] + fx_result["unchanged"] == 1
        portfolios = PortfolioService(db, user.id)
        portfolio = await portfolios.create(
            PortfolioCreate(name="Disposable restore test", base_currency="CHF")
        )
        account = await portfolios.create_account(
            portfolio.id,
            AccountCreate(name="Test broker", account_type="BROKER", default_currency="CHF"),
        )
        await portfolios.create_transaction(
            portfolio.id,
            TransactionInput(
                account_id=account.id,
                type="DEPOSIT",
                trade_date=today,
                amount=Decimal("10000"),
                currency="CHF",
            ),
        )
        await portfolios.create_transaction(
            portfolio.id,
            TransactionInput(
                account_id=account.id,
                instrument_id=instrument.id,
                type="BUY",
                trade_date=today,
                quantity=Decimal("10"),
                price=Decimal("100"),
                currency="USD",
            ),
        )
        value = await PortfolioValuationService(db, user.id).value(portfolio.id, today)
        assert value["status"] == "COMPLETE" and value["total_value_base"] == Decimal("10180")
        print(
            json.dumps(
                {
                    "username": username,
                    "portfolio_id": str(portfolio.id),
                    "raw_id": str(price_preview["raw_ingestion_id"]),
                    "expected_value": str(value["total_value_base"]),
                    "instrument_id": str(instrument.id),
                    "fx_raw_id": str(fx_preview["raw_ingestion_id"]),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
