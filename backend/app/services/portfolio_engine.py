"""Deterministic portfolio ledger. Money stays Decimal until presentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from uuid import UUID

from app.core.errors import AppError
from app.models import Transaction

getcontext().prec = 34
ZERO = Decimal(0)
MONEY_QUANTUM = Decimal("0.00000001")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)


@dataclass
class PositionState:
    account_id: UUID
    instrument_id: UUID
    currency: str
    quantity: Decimal = ZERO
    cost_basis: Decimal | None = ZERO
    realized_pnl: Decimal | None = ZERO

    @property
    def average_cost(self) -> Decimal | None:
        if self.cost_basis is None:
            return None
        return money(self.cost_basis / self.quantity) if self.quantity else ZERO


@dataclass
class LedgerState:
    cash: dict[tuple[UUID, str], Decimal] = field(default_factory=dict)
    positions: dict[tuple[UUID, UUID], PositionState] = field(default_factory=dict)
    income: dict[str, Decimal] = field(default_factory=dict)
    fees: dict[str, Decimal] = field(default_factory=dict)
    taxes: dict[str, Decimal] = field(default_factory=dict)
    external_flows: list[tuple[date, str, Decimal]] = field(default_factory=list)
    realized_events: list[tuple[date, str, Decimal]] = field(default_factory=list)
    income_events: list[tuple[date, str, Decimal]] = field(default_factory=list)
    fee_events: list[tuple[date, str, Decimal]] = field(default_factory=list)
    tax_events: list[tuple[date, str, Decimal]] = field(default_factory=list)
    transaction_ids: list[UUID] = field(default_factory=list)
    opening_dates: list[date] = field(default_factory=list)
    realized_incomplete: bool = False


def _add(bucket: dict[str, Decimal], currency: str, value: Decimal) -> None:
    bucket[currency] = money(bucket.get(currency, ZERO) + value)


def _cash(state: LedgerState, account_id: UUID, currency: str, value: Decimal) -> None:
    key = (account_id, currency)
    state.cash[key] = money(state.cash.get(key, ZERO) + value)


def ledger_state(transactions: list[Transaction], on_date: date, cutoff: datetime) -> LedgerState:
    """Replay visible transactions; a later void leaves earlier PIT history intact."""
    state = LedgerState()
    visible = [
        row
        for row in transactions
        if row.trade_date <= on_date
        and row.created_at <= cutoff
        and (row.voided_at is None or row.voided_at > cutoff)
    ]
    for row in sorted(
        visible,
        key=lambda item: (
            item.trade_date,
            0 if item.type == "OPENING_POSITION" else 1 if item.type == "SPLIT" else 2,
            item.created_at,
            str(item.id),
        ),
    ):
        if (
            row.fee is None
            or row.tax is None
            or any(
                value is not None and not value.is_finite()
                for value in (row.quantity, row.price, row.amount, row.fee, row.tax)
            )
        ):
            raise AppError(422, "INVALID_TRANSACTION", "Missing costs or non-finite ledger value")
        if row.type in {"BUY", "SELL"} and (
            row.quantity is None or row.quantity <= 0 or row.price is None or row.price <= 0
        ):
            raise AppError(
                422, "INVALID_TRANSACTION", "Trade quantity and price must be known and positive"
            )
        if row.type == "SPLIT" and (row.quantity is None or row.quantity <= 0):
            raise AppError(422, "INVALID_TRANSACTION", "Split ratio must be known and positive")
        if row.type in {
            "DEPOSIT",
            "WITHDRAWAL",
            "TRANSFER_IN",
            "TRANSFER_OUT",
            "DIVIDEND",
            "INTEREST",
            "FEE",
            "TAX",
            "CASH_ADJUSTMENT",
        } and (
            row.amount is None
            or (row.type != "CASH_ADJUSTMENT" and row.amount < 0)
            or (
                row.type in {"DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT", "FEE", "TAX"}
                and row.amount == 0
            )
        ):
            raise AppError(422, "INVALID_TRANSACTION", "Cash amount is missing or invalid")
        amount = row.amount or ZERO
        quantity = row.quantity or ZERO
        price = row.price or ZERO
        fee = row.fee or ZERO
        tax = row.tax or ZERO
        if fee < 0 or tax < 0:
            raise AppError(422, "INVALID_TRANSACTION", "Negative fee or tax")
        state.transaction_ids.append(row.id)
        if fee:
            _add(state.fees, row.currency, fee)
            state.fee_events.append((row.trade_date, row.currency, fee))
        if tax:
            _add(state.taxes, row.currency, tax)
            state.tax_events.append((row.trade_date, row.currency, tax))
        if row.type in {"BUY", "SELL", "SPLIT", "OPENING_POSITION"}:
            if row.instrument_id is None:
                raise AppError(422, "INVALID_TRANSACTION", "Instrument required")
            key = (row.account_id, row.instrument_id)
            if row.type == "OPENING_POSITION":
                if (
                    key in state.positions
                    or row.quantity is None
                    or row.quantity <= 0
                    or row.price is not None
                    or row.fee
                    or row.tax
                    or (row.amount is not None and row.amount < 0)
                    or not row.notes
                    or len(row.notes.strip()) < 10
                ):
                    raise AppError(
                        422,
                        "OPENING_POSITION_INVALID",
                        "Opening must precede trades and include source provenance",
                    )
                state.positions[key] = PositionState(
                    row.account_id,
                    row.instrument_id,
                    row.currency,
                    quantity=quantity,
                    cost_basis=row.amount,
                )
                state.opening_dates.append(row.trade_date)
                continue  # No invented purchase, cash movement or historical return.
            position = state.positions.setdefault(
                key, PositionState(row.account_id, row.instrument_id, row.currency)
            )
            if position.currency != row.currency:
                raise AppError(422, "INVALID_TRANSACTION", "Position currency mismatch")
            if row.type == "BUY":
                position.quantity += quantity
                purchase = money(quantity * price + fee + tax)
                if position.cost_basis is not None:
                    position.cost_basis = money(position.cost_basis + purchase)
                _cash(state, row.account_id, row.currency, -purchase)
            elif row.type == "SELL":
                if quantity > position.quantity:
                    raise AppError(409, "INSUFFICIENT_POSITION", "Sell exceeds available quantity")
                sold_cost = (
                    money(position.cost_basis * quantity / position.quantity)
                    if position.cost_basis is not None
                    else None
                )
                position.quantity -= quantity
                if position.cost_basis is not None and sold_cost is not None:
                    position.cost_basis = money(position.cost_basis - sold_cost)
                if not position.quantity:
                    position.cost_basis = ZERO
                proceeds = money(quantity * price - fee - tax)
                if sold_cost is None or position.realized_pnl is None:
                    position.realized_pnl = None
                    state.realized_incomplete = True
                else:
                    position.realized_pnl = money(position.realized_pnl + proceeds - sold_cost)
                    state.realized_events.append(
                        (row.trade_date, row.currency, money(proceeds - sold_cost))
                    )
                _cash(state, row.account_id, row.currency, proceeds)
            else:
                new_quantity = position.quantity * quantity  # quantity is the split ratio
                if new_quantity != money(new_quantity):
                    raise AppError(409, "FRACTIONAL_SPLIT_REVIEW", "Split exceeds share precision")
                position.quantity = new_quantity
        elif row.type in {"DEPOSIT", "TRANSFER_IN"}:
            _cash(state, row.account_id, row.currency, amount)
            state.external_flows.append((row.trade_date, row.currency, amount))
        elif row.type in {"WITHDRAWAL", "TRANSFER_OUT"}:
            _cash(state, row.account_id, row.currency, -amount)
            state.external_flows.append((row.trade_date, row.currency, -amount))
        elif row.type in {"DIVIDEND", "INTEREST"}:
            _cash(state, row.account_id, row.currency, amount - fee - tax)
            _add(state.income, row.currency, amount)
            state.income_events.append((row.trade_date, row.currency, amount))
        elif row.type in {"FEE", "TAX"}:
            _cash(state, row.account_id, row.currency, -amount)
            _add(state.fees if row.type == "FEE" else state.taxes, row.currency, amount)
            (state.fee_events if row.type == "FEE" else state.tax_events).append(
                (row.trade_date, row.currency, amount)
            )
        elif row.type == "CASH_ADJUSTMENT":
            _cash(state, row.account_id, row.currency, amount)
        else:
            raise AppError(422, "INVALID_TRANSACTION", "Unsupported transaction type")
    return state
