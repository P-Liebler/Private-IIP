"""Read-only comparison with an explicitly entered statement, using the P4 ledger."""

from datetime import date
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Instrument
from app.schemas.portfolio import Currency
from app.services.fundamentals import digest
from app.services.market_queries import pit_cutoff
from app.services.portfolio_engine import ZERO, ledger_state, money
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService

Number = Annotated[Decimal, Field(max_digits=28, decimal_places=8)]


class StatementPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: UUID
    quantity: Number
    currency: Currency
    reported_market_value: Number | None = None


class StatementCash(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currency: Currency
    amount: Number


class ReconciliationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    statement_date: date
    source_reference: str = Field(min_length=10, max_length=200)
    complete_statement: bool = False
    positions: list[StatementPosition] = Field(default_factory=list, max_length=100)
    cash: list[StatementCash] = Field(default_factory=list, max_length=3)
    reported_value_base: Number | None = None

    @model_validator(mode="after")
    def distinct(self) -> "ReconciliationInput":
        if len({p.instrument_id for p in self.positions}) != len(self.positions):
            raise ValueError("Duplicate statement position")
        if len({c.currency for c in self.cash}) != len(self.cash):
            raise ValueError("Duplicate statement currency")
        if (
            not self.complete_statement
            and not self.positions
            and not self.cash
            and self.reported_value_base is None
        ):
            raise ValueError(
                "Enter statement fields or explicitly declare a complete empty statement"
            )
        return self


async def reconcile(
    db: AsyncSession, user_id: UUID, portfolio_id: UUID, body: ReconciliationInput
) -> dict[str, object]:
    service = PortfolioService(db, user_id)
    await service.owned(portfolio_id)
    await service.account(portfolio_id, body.account_id)
    cutoff = pit_cutoff(None)
    if body.statement_date > cutoff.date():
        raise AppError(422, "STATEMENT_DATE_INVALID", "Statement date is in the future")
    rows = await service.transactions(portfolio_id)
    state = ledger_state(rows, body.statement_date, cutoff)
    value = await PortfolioValuationService(db, user_id).value(
        portfolio_id, body.statement_date, cutoff
    )
    holdings = {
        UUID(str(h["instrument_id"])): h
        for h in cast(list[dict[str, object]], value["holdings"])
        if h["account_id"] == body.account_id
    }
    stated = {p.instrument_id: p for p in body.positions}
    ids = set(stated) | (set(holdings) if body.complete_statement else set())
    differences: list[dict[str, object]] = []
    for iid in sorted(ids, key=str):
        instrument = await db.get(Instrument, iid)
        if instrument is None:
            raise AppError(
                422, "STATEMENT_INSTRUMENT_UNKNOWN", "Map the statement instrument first"
            )
        position = state.positions.get((body.account_id, iid))
        actual = position.quantity if position else ZERO
        reported = stated[iid].quantity if iid in stated else ZERO
        expected_currency = stated[iid].currency if iid in stated else instrument.currency
        market_value = holdings.get(iid, {}).get("market_value_native")
        reported_market_value = stated[iid].reported_market_value if iid in stated else None
        differences.append(
            {
                "instrument_id": iid,
                "name": instrument.name,
                "reported_quantity": reported,
                "ledger_quantity": actual,
                "quantity_difference": actual - reported,
                "currency_matches": expected_currency == instrument.currency,
                "reported_market_value": reported_market_value,
                "app_market_value": market_value,
                "market_value_difference": money(
                    cast(Decimal, market_value) - reported_market_value
                )
                if market_value is not None and reported_market_value is not None
                else None,
            }
        )
    declared_cash: dict[str, Decimal] = {c.currency: c.amount for c in body.cash}
    actual_cash = {
        currency: amount
        for (account, currency), amount in state.cash.items()
        if account == body.account_id
    }
    currencies = set(declared_cash) | (set(actual_cash) if body.complete_statement else set())
    cash = [
        {
            "currency": c,
            "reported": declared_cash.get(c, ZERO),
            "ledger": actual_cash.get(c, ZERO),
            "difference": money(actual_cash.get(c, ZERO) - declared_cash.get(c, ZERO)),
        }
        for c in sorted(currencies)
    ]
    components = [h["market_value_base"] for h in holdings.values()]
    components += [
        c["base_amount"]
        for c in cast(list[dict[str, object]], value["cash"])
        if c["account_id"] == body.account_id
    ]
    calculated = (
        sum((cast(Decimal, c) for c in components), ZERO)
        if value["status"] == "COMPLETE" and all(c is not None for c in components)
        else None
    )
    reported_value = body.reported_value_base
    nav_difference = (
        money(calculated - reported_value)
        if calculated is not None and reported_value is not None
        else None
    )
    matched = (
        all(
            row["quantity_difference"] == 0
            and row["currency_matches"]
            and row["market_value_difference"] in (None, ZERO)
            for row in differences
        )
        and all(row["difference"] == 0 for row in cash)
        and nav_difference in (None, ZERO)
    )
    incomplete = (reported_value is not None and calculated is None) or any(
        p.reported_market_value is not None
        and (
            p.instrument_id not in holdings
            or holdings[p.instrument_id]["valuation_status"] != "CURRENT"
        )
        for p in body.positions
    )
    return {
        "status": "PARTIAL"
        if incomplete
        else "MATCHED_ENTERED_FIELDS"
        if matched
        else "DIFFERENCES_FOUND",
        "coverage": "COMPLETE_STATEMENT_DECLARED"
        if body.complete_statement
        else "ENTERED_FIELDS_ONLY",
        "source_reference": body.source_reference,
        "statement_date": body.statement_date,
        "knowledge_cutoff": cutoff,
        "input_hash": digest(body.model_dump(mode="json")),
        "positions": differences,
        "cash": cash,
        "calculated_value_base": calculated,
        "reported_value_base": reported_value,
        "value_difference_base": nav_difference,
        "valuation_status": value["status"],
        "transaction_ids": state.transaction_ids,
        "unreviewed_positions": [str(i) for i in set(holdings) - set(stated)]
        if not body.complete_statement
        else [],
        "possible_causes": [
            "MISSING_TRANSACTION",
            "FEE_OR_DIVIDEND",
            "WRONG_INSTRUMENT_OR_EXCHANGE",
            "VALUATION_TIME_OR_FX_REFERENCE",
            "CORPORATE_ACTION_REVIEW",
        ]
        if not matched
        else [],
        "ledger_changed": False,
        "evidence_type": "MANUAL_STATEMENT_ENTRY_NOT_VERIFIED_BROKER_ORIGINAL",
    }
