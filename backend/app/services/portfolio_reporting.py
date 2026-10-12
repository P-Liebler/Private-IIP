from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PortfolioActionApplication, Transaction
from app.services.portfolio_engine import money
from app.services.portfolio_summary import PortfolioSummaryService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService


class PortfolioReportingService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def transaction_amounts(self, row: Transaction, base: str) -> dict[str, object]:
        fx = await PortfolioValuationService(self.db, self.user_id).market.fx(
            row.currency, base, row.trade_date
        )
        rate = cast(Decimal, fx["rate"]) if fx["status"] == "AVAILABLE" else None
        return {
            "base_currency": base,
            "action_locked": row.system_generated
            or bool(
                await self.db.scalar(
                    select(PortfolioActionApplication.id).where(
                        PortfolioActionApplication.transaction_id == row.id
                    )
                )
            ),
            "fx": fx,
            "amount_base": money(row.amount * rate)
            if row.amount is not None and rate is not None
            else None,
            "net_amount_base": money((row.amount - row.fee - row.tax) * rate)
            if row.amount is not None and rate is not None and row.type in {"DIVIDEND", "INTEREST"}
            else None,
        }

    async def dashboard(self) -> dict[str, object]:
        service = PortfolioSummaryService(self.db, self.user_id)
        groups: dict[str, list[dict[str, object]]] = {}
        for portfolio in await PortfolioService(self.db, self.user_id).portfolios():
            groups.setdefault(portfolio.base_currency, []).append(
                await service.summary(portfolio.id)
            )
        aggregates = []
        for currency, summaries in groups.items():
            valuations = [cast(dict[str, object], item["valuation"]) for item in summaries]

            def total(values: list[object]) -> Decimal | None:
                return (
                    sum((cast(Decimal, value) for value in values), Decimal(0))
                    if all(value is not None for value in values)
                    else None
                )

            aggregates.append(
                {
                    "base_currency": currency,
                    "status": "COMPLETE"
                    if all(item["status"] == "COMPLETE" for item in valuations)
                    else "PARTIAL",
                    "total_value_base": total([item["total_value_base"] for item in valuations]),
                    "known_value_base": total([item["known_value_base"] for item in valuations]),
                    "cash_value_base": total([item["cash_value_base"] for item in valuations]),
                    **{
                        key: total([item[key] for item in summaries])
                        for key in ("daily_change_base", "total_return_base", "ytd_return_base")
                    },
                }
            )
        return {
            "aggregation": "GROUPED_BY_BASE_CURRENCY",
            "return_status": "PROVISIONAL",
            "groups": aggregates,
        }

    async def allocation(
        self, portfolio_id: UUID, on_date: date | None = None
    ) -> dict[str, object]:
        result = await PortfolioValuationService(self.db, self.user_id).value(portfolio_id, on_date)
        if result["status"] != "COMPLETE":
            return {
                "status": "PARTIAL",
                "issues": result["issues"],
                "by_instrument": None,
                "by_currency": None,
                "by_asset_type": None,
            }
        holdings = result["holdings"]
        total = cast(Decimal | None, result["total_value_base"])
        if not isinstance(holdings, list) or total is None or total <= 0:
            return {"status": "UNAVAILABLE", "reason": "NON_POSITIVE_PORTFOLIO_VALUE"}
        instrument_values: dict[UUID, Decimal] = {}
        for item in holdings:
            instrument_id = item["instrument_id"]
            amount = item["market_value_base"]
            if amount is not None:
                instrument_values[instrument_id] = (
                    instrument_values.get(instrument_id, Decimal(0)) + amount
                )
        by_instrument = [
            {"instrument_id": key, "value": value, "weight": value / total}
            for key, value in sorted(instrument_values.items(), key=lambda item: str(item[0]))
        ]
        by_currency: dict[str, Decimal] = {}
        by_asset_type: dict[str, Decimal] = {}
        for item in holdings:
            amount = item["market_value_base"]
            if amount is None:
                continue
            currency = str(item["currency"])
            asset_type = str(item["asset_type"])
            by_currency[currency] = by_currency.get(currency, Decimal(0)) + amount
            by_asset_type[asset_type] = by_asset_type.get(asset_type, Decimal(0)) + amount
        for item in cast(list[dict[str, object]], result["cash"]):
            amount = item["base_amount"]
            if amount is not None:
                currency = str(item["currency"])
                by_currency[currency] = by_currency.get(currency, Decimal(0)) + cast(
                    Decimal, amount
                )
                by_asset_type["CASH"] = by_asset_type.get("CASH", Decimal(0)) + cast(
                    Decimal, amount
                )
        return {
            "status": "AVAILABLE",
            "base_currency": result["base_currency"],
            "by_instrument": by_instrument,
            "by_currency": [
                {"currency": key, "value": value, "weight": value / total}
                for key, value in sorted(by_currency.items())
            ],
            "by_asset_type": [
                {"asset_type": key, "value": value, "weight": value / total}
                for key, value in sorted(by_asset_type.items())
            ],
            "cash": result["cash"],
            "issues": [],
        }
