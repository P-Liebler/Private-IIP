from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    CorporateActionVersion,
    DataSource,
    Instrument,
    PortfolioActionApplication,
    Transaction,
)
from app.services.market_queries import MarketQueryService, pit_cutoff
from app.services.portfolio_engine import ZERO, ledger_state, money
from app.services.portfolios import PortfolioService

MAX_PRICE_AGE_DAYS = 7


class PortfolioValuationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.market = MarketQueryService(db)

    async def value(
        self,
        portfolio_id: UUID,
        on_date: date | None = None,
        as_of: datetime | None = None,
        *,
        reporting_currency: str | None = None,
    ) -> dict[str, object]:
        portfolio = await PortfolioService(self.db, self.user_id).owned(portfolio_id)
        base_currency = reporting_currency or portfolio.base_currency
        cutoff = pit_cutoff(as_of)
        if portfolio.created_at > cutoff:
            raise AppError(
                422,
                "PORTFOLIO_NOT_AVAILABLE_AS_OF",
                "Portfolio did not exist at this knowledge cutoff",
            )
        day = on_date or cutoff.date()
        if day > cutoff.date():
            raise AppError(422, "VALUATION_DATE_INVALID", "Valuation date is after as_of")
        rows = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.portfolio_id == portfolio_id)
                )
            ).all()
        )
        state = ledger_state(rows, day, cutoff)
        issues: list[dict[str, object]] = []
        cash: list[dict[str, object]] = []
        holdings: list[dict[str, object]] = []
        known_cash = ZERO
        known_securities = ZERO
        known_cost_basis = ZERO
        known_unrealized = ZERO
        cash_complete = True
        securities_complete = True
        cost_basis_complete = True
        for (account_id, currency), amount in sorted(
            state.cash.items(), key=lambda item: (str(item[0][0]), item[0][1])
        ):
            fx = await self.market.fx(currency, base_currency, day, cutoff)
            fx = await self._source_names(fx)
            rate = cast(Decimal, fx["rate"]) if fx["status"] == "AVAILABLE" else None
            base_amount = money(amount * rate) if rate is not None else None
            if base_amount is None:
                cash_complete = False
                issues.append(
                    {"code": "MISSING_FX", "account_id": account_id, "currency": currency}
                )
            else:
                known_cash += base_amount
            cash.append(
                {
                    "account_id": account_id,
                    "currency": currency,
                    "amount": amount,
                    "base_amount": base_amount,
                    "fx": fx,
                }
            )
            if amount < 0:
                issues.append(
                    {"code": "NEGATIVE_CASH", "account_id": account_id, "currency": currency}
                )
        for (account_id, instrument_id), position in sorted(
            state.positions.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
        ):
            if position.quantity == 0:
                continue
            if position.cost_basis is None:
                cost_basis_complete = False
                issues.append({"code": "UNKNOWN_COST_BASIS", "instrument_id": instrument_id})
            instrument = await self.db.get(Instrument, instrument_id)
            assert instrument is not None
            price_history = await self.market.prices(
                instrument_id, day - timedelta(days=3650), day, cutoff
            )
            prices = cast(list[dict[str, object]], price_history["prices"])
            latest = prices[-1] if prices else None
            source = await self.db.get(DataSource, latest["source_id"]) if latest else None
            price_day = cast(date, latest["date"]) if latest else None
            age = (day - price_day).days if price_day else None
            price = cast(Decimal, latest["close"]) if latest else None
            price_status = (
                "MISSING_PRICE"
                if price is None
                else "STALE_PRICE"
                if age is not None and age > MAX_PRICE_AGE_DAYS
                else "CURRENT"
            )
            if price_day is not None and any(
                row.account_id == account_id
                and row.instrument_id == instrument_id
                and row.type in {"SPLIT", "DIVIDEND"}
                and price_day < row.trade_date <= day
                and row.created_at <= cutoff
                and (row.voided_at is None or row.voided_at > cutoff)
                for row in rows
            ):
                price_status = "MISSING_EVENT_PRICE"
            # A pre-split quote has a different share unit; never multiply it by post-split shares.
            native = (
                money(position.quantity * price)
                if price is not None and price_status != "MISSING_EVENT_PRICE"
                else None
            )
            if price_status != "CURRENT":
                securities_complete = False
                issues.append(
                    {"code": price_status, "instrument_id": instrument_id, "price_date": price_day}
                )
            fx = await self.market.fx(position.currency, base_currency, day, cutoff)
            fx = await self._source_names(fx)
            rate = cast(Decimal, fx["rate"]) if fx["status"] == "AVAILABLE" else None
            base_value = money(native * rate) if native is not None and rate is not None else None
            if native is not None and rate is None:
                securities_complete = False
                issues.append(
                    {
                        "code": "MISSING_FX",
                        "instrument_id": instrument_id,
                        "currency": position.currency,
                    }
                )
            if (
                base_value is not None
                and rate is not None
                and native is not None
                and price_status == "CURRENT"
            ):
                known_securities += base_value
                if position.cost_basis is not None:
                    known_cost_basis += money(position.cost_basis * rate)
                    known_unrealized += money((native - position.cost_basis) * rate)
            unresolved = await self._unapplied_actions(account_id, instrument_id, rows, day, cutoff)
            if unresolved:
                securities_complete = False
                issues.append(
                    {
                        "code": "UNVERIFIED_CORPORATE_ACTION",
                        "account_id": account_id,
                        "instrument_id": instrument_id,
                        "action_version_ids": unresolved,
                    }
                )
            delisted = await self.db.scalar(
                select(PortfolioActionApplication.id).where(
                    PortfolioActionApplication.account_id == account_id,
                    PortfolioActionApplication.instrument_id == instrument_id,
                    PortfolioActionApplication.action_type == "DELISTING",
                    PortfolioActionApplication.action_date <= day,
                    PortfolioActionApplication.applied_at <= cutoff,
                )
            )
            if delisted is not None:
                securities_complete = False
                issues.append(
                    {
                        "code": "DELISTED_POSITION_REVIEW",
                        "account_id": account_id,
                        "instrument_id": instrument_id,
                    }
                )
            holdings.append(
                {
                    "account_id": account_id,
                    "instrument_id": instrument_id,
                    "name": instrument.name,
                    "ticker": instrument.ticker,
                    "isin": instrument.isin,
                    "mic": instrument.mic,
                    "asset_type": instrument.asset_type,
                    "quantity": position.quantity,
                    "average_cost_native": position.average_cost,
                    "cost_basis_native": position.cost_basis,
                    "realized_pnl_native": position.realized_pnl,
                    "currency": position.currency,
                    "price": price,
                    "price_date": price_day,
                    "price_age_days": age,
                    "price_version_id": latest["id"] if latest else None,
                    "price_source_id": latest["source_id"] if latest else None,
                    "price_source_name": source.name if source else None,
                    "price_observed_at": latest["observed_at"] if latest else None,
                    "price_kind": "DAILY_CLOSE_NOT_LIVE",
                    "market_data_state": "HISTORICAL_ONLY"
                    if on_date is not None and day < cutoff.date()
                    else {
                        "CURRENT": "DELAYED",
                        "STALE_PRICE": "STALE",
                        "MISSING_PRICE": "MISSING",
                        "MISSING_EVENT_PRICE": "INVALID",
                    }.get(price_status, "MISSING"),
                    "collection_state": "SOURCE_BLOCKED"
                    if source and (source.gate_status != "APPROVED" or not source.enabled)
                    else "MANUAL_IMPORT"
                    if source and source.slug == "MANUAL_CSV"
                    else "SOURCE_GATE_REQUIRED",
                    "price_quality": latest["quality_label"] if latest else None,
                    "market_value_native": native,
                    "market_value_base": base_value,
                    "cost_basis_base_at_valuation_fx": money(position.cost_basis * rate)
                    if rate is not None and position.cost_basis is not None
                    else None,
                    "unrealized_pnl_base_at_valuation_fx": money(
                        (native - position.cost_basis) * rate
                    )
                    if native is not None and rate is not None and position.cost_basis is not None
                    else None,
                    "fx": fx,
                    "unrealized_pnl_native": native - position.cost_basis
                    if native is not None and position.cost_basis is not None
                    else None,
                    "valuation_status": price_status
                    if price_status != "CURRENT"
                    else "MISSING_FX"
                    if rate is None
                    else "CURRENT",
                }
            )
        for (account_id, instrument_id), position in state.positions.items():
            if position.quantity != 0:
                continue
            unresolved = await self._unapplied_actions(account_id, instrument_id, rows, day, cutoff)
            if unresolved:
                securities_complete = False
                issues.append(
                    {
                        "code": "UNVERIFIED_CORPORATE_ACTION",
                        "account_id": account_id,
                        "instrument_id": instrument_id,
                        "action_version_ids": unresolved,
                    }
                )
        complete = cash_complete and securities_complete
        status = "COMPLETE" if complete else "PARTIAL"
        known_value = known_cash + known_securities
        total = known_value if complete else None
        for holding in holdings:
            base_value = cast(Decimal | None, holding["market_value_base"])
            holding["weight"] = (
                base_value / total
                if total is not None and total > 0 and base_value is not None
                else None
            )
        realized_base = await self._historical_sum(state.realized_events, base_currency, cutoff)
        if state.realized_incomplete:
            realized_base = None
            issues.append({"code": "UNKNOWN_REALIZED_COST_BASIS"})
        income_base = await self._historical_sum(state.income_events, base_currency, cutoff)
        fees_base = await self._historical_sum(state.fee_events, base_currency, cutoff)
        taxes_base = await self._historical_sum(state.tax_events, base_currency, cutoff)
        if any(
            events
            and amount is None
            and not (events is state.realized_events and state.realized_incomplete)
            for events, amount in (
                (state.realized_events, realized_base),
                (state.income_events, income_base),
                (state.fee_events, fees_base),
                (state.tax_events, taxes_base),
            )
        ):
            issues.append({"code": "MISSING_EVENT_FX"})
        event_fx = []
        for event_day, currency in sorted(
            {
                (d, c)
                for events in (
                    state.realized_events,
                    state.income_events,
                    state.fee_events,
                    state.tax_events,
                )
                for d, c, _ in events
            }
        ):
            event_fx.append(await self.market.fx(currency, base_currency, event_day, cutoff))
        return {
            "portfolio_id": portfolio_id,
            "name": portfolio.name,
            "on_date": day,
            "as_of": cutoff,
            "base_currency": base_currency,
            "status": status,
            "analytics_status": "PARTIAL"
            if any(
                issue["code"]
                in {"MISSING_EVENT_FX", "UNKNOWN_COST_BASIS", "UNKNOWN_REALIZED_COST_BASIS"}
                for issue in issues
            )
            else status,
            "issues": issues,
            "cash": cash,
            "holdings": holdings,
            "cash_value_base": known_cash if cash_complete else None,
            "securities_value_base": known_securities if securities_complete else None,
            "known_value_base": known_value,
            "total_value_base": total,
            "cost_basis_base_at_valuation_fx": known_cost_basis
            if securities_complete and cost_basis_complete
            else None,
            "unrealized_pnl_base_at_valuation_fx": known_unrealized
            if securities_complete and cost_basis_complete
            else None,
            "realized_pnl_base_at_trade_fx": realized_base,
            "income_base_at_event_fx": income_base,
            "fees_base_at_event_fx": fees_base,
            "taxes_base_at_event_fx": taxes_base,
            "income_native": state.income,
            "fees_native": state.fees,
            "taxes_native": state.taxes,
            "transaction_ids": state.transaction_ids,
            "event_fx_provenance": event_fx,
        }

    async def _historical_sum(
        self, events: list[tuple[date, str, Decimal]], base_currency: str, cutoff: datetime
    ) -> Decimal | None:
        total = ZERO
        rates: dict[tuple[date, str], Decimal] = {}
        for day, currency, amount in events:
            key = (day, currency)
            if key not in rates:
                fx = await self.market.fx(currency, base_currency, day, cutoff)
                if fx["status"] != "AVAILABLE":
                    return None
                rates[key] = cast(Decimal, fx["rate"])
            total += money(amount * rates[key])
        return money(total)

    async def _source_names(self, fx: dict[str, object]) -> dict[str, object]:
        names = []
        for source_id in cast(list[UUID], fx.get("source_ids", [])):
            source = await self.db.get(DataSource, source_id)
            if source:
                names.append(source.name)
        return {**fx, "source_names": names}

    async def _unapplied_actions(
        self,
        account_id: UUID,
        instrument_id: UUID,
        rows: list[Transaction],
        day: date,
        cutoff: datetime,
    ) -> list[UUID]:
        purchases = [
            row.trade_date
            for row in rows
            if row.account_id == account_id
            and row.instrument_id == instrument_id
            and row.type in {"BUY", "OPENING_POSITION"}
            and row.created_at <= cutoff
            and (row.voided_at is None or row.voided_at > cutoff)
        ]
        if not purchases:
            return []
        actions = list(
            (
                await self.db.scalars(
                    select(CorporateActionVersion)
                    .where(
                        CorporateActionVersion.instrument_id == instrument_id,
                        CorporateActionVersion.action_date > min(purchases),
                        CorporateActionVersion.action_date <= day,
                        CorporateActionVersion.known_at <= cutoff,
                    )
                    .order_by(CorporateActionVersion.known_at.desc())
                )
            ).all()
        )
        latest: dict[tuple[date, str], CorporateActionVersion] = {}
        for action in actions:
            latest.setdefault((action.action_date, action.action_type), action)
        applied = list(
            (
                await self.db.scalars(
                    select(PortfolioActionApplication).where(
                        PortfolioActionApplication.account_id == account_id,
                        PortfolioActionApplication.instrument_id == instrument_id,
                        PortfolioActionApplication.action_date <= day,
                        PortfolioActionApplication.applied_at <= cutoff,
                    )
                )
            ).all()
        )
        applied_keys = {
            (row.action_date, row.action_type, row.action_version_id) for row in applied
        }
        return [
            action.id
            for action in latest.values()
            if (action.action_date, action.action_type, action.id) not in applied_keys
            and (
                (
                    held := ledger_state(
                        rows, action.action_date - timedelta(days=1), cutoff
                    ).positions.get((account_id, instrument_id))
                )
                is not None
                and held.quantity > 0
            )
        ]
