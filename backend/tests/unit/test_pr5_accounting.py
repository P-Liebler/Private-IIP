"""Synthetic opening balances, unknown costs and import idempotency contracts."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.models import Transaction
from app.schemas.portfolio import TransactionInput
from app.services.portfolio_engine import ledger_state
from app.services.portfolio_import import duplicate_status, plan_hash
from app.services.portfolios import transaction_fingerprint

DAY = date(2025, 1, 2)
CUTOFF = datetime(2026, 1, 1, tzinfo=UTC)


def row(account, instrument, kind, **values):
    payload = TransactionInput(
        account_id=account,
        instrument_id=instrument,
        type=kind,
        trade_date=DAY,
        currency="CHF",
        **values,
    )
    return Transaction(
        id=uuid4(),
        portfolio_id=uuid4(),
        **payload.model_dump(),
        status="ACTIVE",
        fingerprint=transaction_fingerprint(payload),
        created_at=datetime(2025, 1, 3, tzinfo=UTC),
        voided_at=None,
    )


def test_unknown_opening_cost_is_not_a_purchase_cashflow_or_zero_cost():
    account, instrument = uuid4(), uuid4()
    opening = row(
        account, instrument, "OPENING_POSITION", quantity="10", notes="SYNTHETIC opening statement"
    )
    state = ledger_state([opening], DAY, CUTOFF)
    position = state.positions[(account, instrument)]
    assert position.quantity == 10 and position.cost_basis is None and position.average_cost is None
    assert state.cash == {} and state.external_flows == [] and state.opening_dates == [DAY]


def test_known_opening_cost_fees_taxes_partial_sale_split_and_dividend():
    account, instrument = uuid4(), uuid4()
    opening = row(
        account,
        instrument,
        "OPENING_POSITION",
        quantity="10",
        amount="100",
        notes="SYNTHETIC opening statement",
    )
    buy = row(account, instrument, "BUY", quantity="2", price="20", fee="1", tax="1")
    sell = row(account, instrument, "SELL", quantity="3", price="30", fee="2", tax="1")
    split = row(account, instrument, "SPLIT", quantity="2")
    income = row(account, instrument, "DIVIDEND", amount="5", tax="1")
    for n, event in enumerate((buy, sell, split, income), 1):
        event.trade_date = DAY + timedelta(days=n)
    state = ledger_state([opening, buy, sell, split, income], DAY + timedelta(days=5), CUTOFF)
    position = state.positions[(account, instrument)]
    assert position.quantity == 18 and position.cost_basis == Decimal("106.5")
    assert position.realized_pnl == Decimal("51.5")
    assert state.cash[(account, "CHF")] == 49


def test_unknown_opening_cost_remains_unknown_after_sale():
    account, instrument = uuid4(), uuid4()
    opening = row(
        account, instrument, "OPENING_POSITION", quantity="2", notes="SYNTHETIC opening statement"
    )
    sell = row(account, instrument, "SELL", quantity="2", price="10")
    sell.trade_date += timedelta(days=1)
    state = ledger_state([opening, sell], sell.trade_date, CUTOFF)
    assert state.cash[(account, "CHF")] == 20
    assert state.positions[(account, instrument)].realized_pnl is None
    assert state.realized_incomplete and state.realized_events == []


def test_opening_after_existing_history_is_rejected():
    account, instrument = uuid4(), uuid4()
    buy = row(account, instrument, "BUY", quantity="2", price="10")
    opening = row(
        account, instrument, "OPENING_POSITION", quantity="2", notes="SYNTHETIC opening statement"
    )
    opening.trade_date += timedelta(days=1)
    with pytest.raises(AppError, match="Opening must precede"):
        ledger_state([buy, opening], opening.trade_date, CUTOFF)


@pytest.mark.parametrize(
    "changes", [{"notes": ""}, {"price": "10"}, {"quantity": "-1"}, {"amount": "-1"}, {"fee": "1"}]
)
def test_invalid_opening_entry_cannot_post(changes):
    body = dict(
        account_id=uuid4(),
        instrument_id=uuid4(),
        type="OPENING_POSITION",
        trade_date=DAY,
        currency="CHF",
        quantity="2",
        notes="SYNTHETIC opening statement",
    )
    with pytest.raises(ValidationError):
        TransactionInput(**(body | changes))


def test_import_does_not_resurrect_voided_original_or_hide_changed_external_id():
    account, instrument = uuid4(), uuid4()
    original = row(
        account, instrument, "BUY", quantity="2", price="10", external_id="synthetic-001"
    )
    original.status, original.voided_at = "VOIDED", CUTOFF
    payload = TransactionInput(
        account_id=account,
        instrument_id=instrument,
        type="BUY",
        trade_date=DAY,
        currency="CHF",
        quantity="2",
        price="10",
        external_id="synthetic-001",
    )
    assert duplicate_status(payload, [original]) == "DUPLICATE"
    changed = payload.model_copy(update={"price": Decimal("11")})
    assert duplicate_status(changed, [original]) == "CONFLICT"


def test_preview_plan_binds_explicit_choices_and_mapping():
    instrument = uuid4()
    assert plan_hash({"a": "type", "b": "currency"}, {}) == plan_hash(
        {"b": "currency", "a": "type"}, {}
    )
    assert plan_hash(None, {}) != plan_hash(None, {2: instrument})
