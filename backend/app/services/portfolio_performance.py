"""Portfolio return calculations from complete point-in-time valuations."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Benchmark, Instrument, Transaction
from app.services.market_queries import pit_cutoff
from app.services.portfolio_engine import ZERO, ledger_state
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService

ONE = Decimal(1)
DAYS_IN_YEAR = Decimal("365.2425")


def xirr(flows: list[tuple[date, Decimal]]) -> Decimal | None:
    """Solve annualized IRR on [-99.99%, 100000%]; reject ambiguous roots."""
    combined: dict[date, Decimal] = {}
    for day, amount in flows:
        combined[day] = combined.get(day, ZERO) + amount
    items = sorted(combined.items())
    if len(items) < 2 or not any(v < 0 for _, v in items) or not any(v > 0 for _, v in items):
        return None
    signs = [1 if amount > 0 else -1 for _, amount in items if amount]
    if sum(left != right for left, right in zip(signs, signs[1:], strict=False)) != 1:
        return None  # Non-conventional flows can have multiple economically ambiguous roots.
    start = items[0][0]

    def npv(rate: Decimal) -> Decimal:
        with localcontext() as context:
            context.prec = 34
            return sum(
                (
                    amount / (ONE + rate) ** (Decimal((day - start).days) / DAYS_IN_YEAR)
                    for day, amount in items
                ),
                ZERO,
            )

    try:
        grid = [
            Decimal("-0.9999"),
            Decimal("-0.99"),
            Decimal("-0.9"),
            Decimal("-0.5"),
            ZERO,
            ONE,
            Decimal(5),
            Decimal(20),
            Decimal(100),
            Decimal(1000),
        ]
        brackets = [
            (left, right)
            for left, right in zip(grid, grid[1:], strict=False)
            if npv(left) == 0 or npv(left) * npv(right) < 0
        ]
        if len(brackets) != 1:
            return None
        low, high = brackets[0]
        low_value = npv(low)
        for _ in range(180):
            middle = (low + high) / 2
            value = npv(middle)
            if abs(value) < Decimal("0.00000001"):
                return middle
            if (value < 0) == (low_value < 0):
                low, low_value = middle, value
            else:
                high = middle
        return (low + high) / 2
    except (InvalidOperation, OverflowError):
        return None


def twr_period(
    previous_value: Decimal, ending_value: Decimal, external_flow: Decimal
) -> Decimal | None:
    """End-of-day flow convention. A zero opening capital has no defined return."""
    if previous_value <= 0:
        return None
    return (ending_value - external_flow) / previous_value - ONE


class PortfolioPerformanceService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.valuation = PortfolioValuationService(db, user_id)

    async def benchmark(
        self, portfolio_id: UUID, start: date, end: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        portfolio = await PortfolioService(self.db, self.user_id).owned(portfolio_id)
        cutoff = pit_cutoff(as_of)
        if start > end or end > cutoff.date():
            raise AppError(422, "BENCHMARK_RANGE_INVALID", "Invalid benchmark range")
        benchmark = (
            await self.db.get(Benchmark, portfolio.benchmark_id) if portfolio.benchmark_id else None
        )
        if benchmark is None:
            return {"status": "DATA_UNAVAILABLE", "reason": "NO_BENCHMARK"}
        instrument = await self.db.get(Instrument, benchmark.instrument_id)
        assert instrument is not None
        market = self.valuation.market
        first = cast(
            list[dict[str, object]],
            (await market.prices(instrument.id, start - timedelta(days=7), start, cutoff))[
                "prices"
            ],
        )
        last = cast(
            list[dict[str, object]],
            (await market.prices(instrument.id, end - timedelta(days=7), end, cutoff))["prices"],
        )
        if not first or not last:
            return {"status": "DATA_UNAVAILABLE", "reason": "MISSING_BENCHMARK_PRICE"}
        opening, closing = first[-1], last[-1]
        start_fx = await market.fx(instrument.currency, portfolio.base_currency, start, cutoff)
        end_fx = await market.fx(instrument.currency, portfolio.base_currency, end, cutoff)
        if start_fx["status"] != "AVAILABLE" or end_fx["status"] != "AVAILABLE":
            return {"status": "DATA_UNAVAILABLE", "reason": "MISSING_BENCHMARK_FX"}
        shares, cash_base = ONE, ZERO
        actions = cast(
            list[dict[str, object]],
            (await market.actions(instrument.id, cast(date, opening["date"]), end, cutoff))[
                "actions"
            ],
        )
        for action in sorted(
            actions,
            key=lambda item: (
                cast(date, item["date"]),
                0 if item["type"] in {"SPLIT", "REVERSE_SPLIT"} else 1,
            ),
        ):
            if cast(date, action["date"]) <= cast(date, opening["date"]):
                continue
            if action["type"] in {"SPLIT", "REVERSE_SPLIT"}:
                shares *= cast(Decimal, action["ratio"])
            elif action["type"] == "DIVIDEND":
                fx = await market.fx(
                    cast(str, action["currency"] or instrument.currency),
                    portfolio.base_currency,
                    cast(date, action["date"]),
                    cutoff,
                )
                if fx["status"] != "AVAILABLE":
                    return {"status": "DATA_UNAVAILABLE", "reason": "MISSING_BENCHMARK_DIVIDEND_FX"}
                cash_base += (
                    shares * cast(Decimal, action["cash_amount"]) * cast(Decimal, fx["rate"])
                )
            elif action["type"] == "DELISTING":
                return {"status": "DATA_UNAVAILABLE", "reason": "BENCHMARK_DELISTED"}
        opening_base = cast(Decimal, opening["close"]) * cast(Decimal, start_fx["rate"])
        ending_base = (
            shares * cast(Decimal, closing["close"]) * cast(Decimal, end_fx["rate"]) + cash_base
        )
        return {
            "status": "PROVISIONAL",
            "action_coverage": "UNVERIFIED",
            "benchmark_id": benchmark.id,
            "name": benchmark.name,
            "return_base": ending_base / opening_base - ONE,
            "base_currency": portfolio.base_currency,
            "basis": "RAW_CLOSE_EXPLICIT_ACTIONS_NON_REINVESTED_INCOME",
            "start_price_date": opening["date"],
            "end_price_date": closing["date"],
            "price_version_ids": [opening["id"], closing["id"]],
            "action_version_ids": [action["id"] for action in actions],
        }

    async def _opening_exposure_fx_effect(
        self, prior: dict[str, object], day: date, base_currency: str, cutoff: datetime
    ) -> Decimal | None:
        """Translate prior close holdings and cash at today's FX, before today's trades."""
        exposure: dict[str, Decimal] = {}
        old_rates: dict[str, Decimal] = {}
        for cash in cast(list[dict[str, object]], prior["cash"]):
            currency = cast(str, cash["currency"])
            exposure[currency] = exposure.get(currency, ZERO) + cast(Decimal, cash["amount"])
            old_rates[currency] = cast(Decimal, cast(dict[str, object], cash["fx"])["rate"])
        for holding in cast(list[dict[str, object]], prior["holdings"]):
            currency = cast(str, holding["currency"])
            native = cast(Decimal | None, holding["market_value_native"])
            if native is None:
                return None
            exposure[currency] = exposure.get(currency, ZERO) + native
            old_rates[currency] = cast(Decimal, cast(dict[str, object], holding["fx"])["rate"])
        effect = ZERO
        for currency, native in exposure.items():
            current = await self.valuation.market.fx(currency, base_currency, day, cutoff)
            if current["status"] != "AVAILABLE":
                return None
            effect += native * (cast(Decimal, current["rate"]) - old_rates[currency])
        return effect

    async def performance(
        self,
        portfolio_id: UUID,
        start: date,
        end: date,
        as_of: datetime | None = None,
        frequency: str = "daily",
    ) -> dict[str, object]:
        portfolio = await PortfolioService(self.db, self.user_id).owned(portfolio_id)
        cutoff = pit_cutoff(as_of)
        if end < start or end > cutoff.date() or (end - start).days > 3650:
            raise AppError(422, "PERFORMANCE_RANGE_INVALID", "Invalid performance date range")
        if frequency not in {"daily", "weekly", "monthly"}:
            raise AppError(422, "FREQUENCY_INVALID", "Use daily, weekly or monthly")
        rows = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.portfolio_id == portfolio_id)
                )
            ).all()
        )
        flow_by_day: dict[date, Decimal] = {}
        missing_flow_fx: list[date] = []
        for day, currency, amount in ledger_state(rows, end, cutoff).external_flows:
            if day <= start:
                continue
            fx = await self.valuation.market.fx(currency, portfolio.base_currency, day, cutoff)
            if fx["status"] != "AVAILABLE":
                missing_flow_fx.append(day)
            else:
                flow_by_day[day] = flow_by_day.get(day, ZERO) + amount * cast(Decimal, fx["rate"])
        series: list[dict[str, object]] = []
        day = start
        product = ONE
        prior: Decimal | None = None
        first: Decimal | None = None
        incomplete = bool(missing_flow_fx)
        undefined_twr = False
        prior_valuation: dict[str, object] | None = None
        fx_contribution = ZERO
        fx_complete = True
        while day <= end:
            valuation = await self.valuation.value(portfolio_id, day, cutoff)
            value = cast(Decimal | None, valuation["total_value_base"])
            if value is None:
                incomplete = True
            if first is None and day == start:
                first = value
            flow = flow_by_day.get(day, ZERO)
            if day > start and prior_valuation is not None and prior is not None:
                effect = await self._opening_exposure_fx_effect(
                    prior_valuation, day, portfolio.base_currency, cutoff
                )
                if effect is None:
                    fx_complete = False
                else:
                    fx_contribution += effect
            daily_return = None
            if day > start and value is not None and prior is not None:
                daily_return = twr_period(prior, value, flow)
                if daily_return is None and (value != flow or prior != 0):
                    undefined_twr = True
                elif daily_return is not None:
                    product *= ONE + daily_return
            elif day > start and value is not None and prior is None:
                undefined_twr = True
            if (
                day == start
                or day == end
                or frequency == "daily"
                or (frequency == "weekly" and day.weekday() == 6)
                or (frequency == "monthly" and (day + timedelta(days=1)).month != day.month)
            ):
                series.append(
                    {
                        "date": day,
                        "status": valuation["status"],
                        "value_base": value,
                        "external_flow_base": None
                        if day in missing_flow_fx
                        else flow
                        if day > start
                        else ZERO,
                        "daily_return": daily_return if frequency == "daily" else None,
                    }
                )
            prior = value
            prior_valuation = valuation
            day += timedelta(days=1)
        finish = prior
        if incomplete or first is None or finish is None:
            return {
                "status": "DATA_UNAVAILABLE",
                "completeness": "PARTIAL",
                "base_currency": portfolio.base_currency,
                "return_status": "PROVISIONAL",
                "benchmark": await self.benchmark(portfolio_id, start, end, cutoff),
                "reason": "INCOMPLETE_VALUATION_OR_FX",
                "missing_flow_fx_dates": missing_flow_fx,
                "series": series,
                "absolute_return_base": None,
                "twr": None,
                "xirr": None,
                "cagr": None,
                "fx_contribution_base": None,
            }
        net_flows = sum(flow_by_day.values(), ZERO)
        absolute = finish - first - net_flows
        flows = [(start, -first)] + [(d, -v) for d, v in flow_by_day.items()] + [(end, finish)]
        days = (end - start).days
        twr = product - ONE if not undefined_twr and days > 0 else None
        cagr = None
        if twr is not None and days > 0 and product > 0:
            cagr = product ** (DAYS_IN_YEAR / Decimal(days)) - ONE
        final_state = ledger_state(rows, end, cutoff)
        event_totals = {}
        for label, events in (
            ("income_base", final_state.income_events),
            ("fees_base", final_state.fee_events),
            ("taxes_base", final_state.tax_events),
        ):
            event_totals[label] = await self.valuation._historical_sum(
                [event for event in events if start < event[0] <= end],
                portfolio.base_currency,
                cutoff,
            )
        return {
            "status": "AVAILABLE",
            "completeness": "COMPLETE",
            "return_status": "PROVISIONAL",
            "action_coverage": "UNVERIFIED",
            "benchmark": await self.benchmark(portfolio_id, start, end, cutoff),
            **event_totals,
            "start": start,
            "end": end,
            "base_currency": portfolio.base_currency,
            "series": series,
            "absolute_return_base": absolute,
            "twr": twr,
            "xirr": xirr(flows),
            "cagr": cagr,
            "fx_contribution_base": fx_contribution if fx_complete else None,
            "fx_contribution_status": "AVAILABLE" if fx_complete else "DATA_UNAVAILABLE",
            "fx_contribution_method": "OPENING_EXPOSURE_DAILY_FX_TRANSLATION",
            "flow_convention": "END_OF_DAY",
            "reason": "UNDEFINED_OPENING_CAPITAL" if undefined_twr else None,
        }
