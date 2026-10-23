from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_queries import pit_cutoff
from app.services.portfolio_engine import ZERO, ledger_state, money
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService


class PortfolioSummaryService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.valuation = PortfolioValuationService(db, user_id)

    async def summary(self, portfolio_id: UUID) -> dict[str, object]:
        cutoff = pit_cutoff(None)
        day = cutoff.date()
        current = await self.valuation.value(portfolio_id, day, cutoff)
        rows = await PortfolioService(self.db, self.user_id).transactions(portfolio_id)
        flows = ledger_state(rows, day, cutoff).external_flows
        opening_dates = ledger_state(rows, day, cutoff).opening_dates
        base = cast(str, current["base_currency"])

        async def net_after(start: date | None) -> Decimal | None:
            result = ZERO
            for event_day, currency, amount in flows:
                if start is not None and event_day <= start:
                    continue
                fx = await self.valuation.market.fx(currency, base, event_day, cutoff)
                if fx["status"] != "AVAILABLE":
                    return None
                result += money(amount * cast(Decimal, fx["rate"]))
            return money(result)

        total = cast(Decimal | None, current["total_value_base"])
        lifetime_flows = await net_after(None)
        result: dict[str, object] = {
            "valuation": current,
            "total_return_base": money(total - lifetime_flows)
            if total is not None and lifetime_flows is not None and not opening_dates
            else None,
        }
        for label, start in (
            ("daily_change_base", day - timedelta(days=1)),
            ("ytd_return_base", date(day.year - 1, 12, 31)),
        ):
            opening = await self.valuation.value(portfolio_id, start, cutoff)
            opening_value = cast(Decimal | None, opening["total_value_base"])
            external = await net_after(start)
            result[label] = (
                money(total - opening_value - external)
                if (
                    total is not None
                    and opening_value is not None
                    and external is not None
                    and not any(start < d <= day for d in opening_dates)
                )
                else None
            )
        result["return_basis"] = "ABSOLUTE_NET_OF_EXTERNAL_FLOWS"
        result["action_coverage"] = "UNVERIFIED"
        result["return_status"] = "PROVISIONAL"
        if opening_dates:
            result["historical_return_limit"] = "OPENING_POSITION_IS_NOT_VERIFIED_TRADE_HISTORY"
        return result
