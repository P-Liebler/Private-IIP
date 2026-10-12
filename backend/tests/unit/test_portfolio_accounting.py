import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.models import Transaction
from app.services.portfolio_engine import ledger_state
from app.services.portfolio_performance import PortfolioPerformanceService, twr_period, xirr


def make_row(
    account_id,
    instrument_id,
    kind,
    day,
    *,
    quantity=None,
    price=None,
    amount=None,
    fee="0",
    tax="0",
    currency="USD",
):
    return Transaction(
        id=uuid4(),
        portfolio_id=uuid4(),
        account_id=account_id,
        instrument_id=instrument_id,
        type=kind,
        trade_date=day,
        quantity=Decimal(quantity) if quantity is not None else None,
        price=Decimal(price) if price is not None else None,
        amount=Decimal(amount) if amount is not None else None,
        fee=Decimal(fee),
        tax=Decimal(tax),
        currency=currency,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        voided_at=None,
    )


def test_weighted_average_cost_split_dividend_and_partial_sell() -> None:
    account, instrument = uuid4(), uuid4()
    day = date(2025, 1, 2)
    rows = [
        make_row(account, None, "DEPOSIT", day, amount="10000"),
        make_row(account, instrument, "BUY", day, quantity="10", price="100", fee="2"),
        make_row(
            account, instrument, "BUY", day + timedelta(days=1), quantity="10", price="120", fee="2"
        ),
        make_row(account, instrument, "SPLIT", day + timedelta(days=2), quantity="2"),
        make_row(account, instrument, "DIVIDEND", day + timedelta(days=3), amount="40", tax="6"),
        make_row(
            account,
            instrument,
            "SELL",
            day + timedelta(days=4),
            quantity="10",
            price="70",
            fee="3",
            tax="1",
        ),
    ]
    state = ledger_state(rows, day + timedelta(days=4), datetime(2025, 2, 1, tzinfo=UTC))
    position = state.positions[(account, instrument)]
    assert position.quantity == Decimal(30)
    assert position.cost_basis == Decimal(1653)
    assert position.average_cost == Decimal("55.1")
    assert position.realized_pnl == Decimal(145)
    assert state.cash[(account, "USD")] == Decimal(8526)
    assert state.income["USD"] == Decimal(40)
    assert state.fees["USD"] == Decimal(7)
    assert state.taxes["USD"] == Decimal(7)


def test_oversell_and_void_point_in_time() -> None:
    account, instrument = uuid4(), uuid4()
    buy = make_row(account, instrument, "BUY", date(2025, 1, 2), quantity="2", price="10")
    sell = make_row(account, instrument, "SELL", date(2025, 1, 3), quantity="3", price="12")
    with pytest.raises(AppError) as error:
        ledger_state([buy, sell], date(2025, 1, 3), datetime(2025, 2, 1, tzinfo=UTC))
    assert error.value.code == "INSUFFICIENT_POSITION"
    buy.voided_at = datetime(2025, 1, 10, tzinfo=UTC)
    before = ledger_state([buy], date(2025, 1, 3), datetime(2025, 1, 5, tzinfo=UTC))
    after = ledger_state([buy], date(2025, 1, 3), datetime(2025, 1, 11, tzinfo=UTC))
    assert before.positions[(account, instrument)].quantity == Decimal(2)
    assert after.positions == {}


def test_twr_neutralizes_external_flow_and_xirr() -> None:
    assert twr_period(Decimal(100), Decimal(160), Decimal(50)) == Decimal("0.1")
    assert twr_period(Decimal(0), Decimal(50), Decimal(50)) is None
    result = xirr([(date(2024, 1, 1), Decimal(-100)), (date(2025, 1, 1), Decimal(110))])
    assert result is not None
    assert abs(result - Decimal("0.1")) < Decimal("0.001")
    assert xirr([(date(2024, 1, 1), Decimal(-100)), (date(2025, 1, 1), Decimal(-10))]) is None


def test_golden_fixture_market_value_and_fx() -> None:
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/portfolio/portfolio_golden_001.json").read_text()
    )
    account, instrument = uuid4(), uuid4()
    rows = [
        make_row(
            account,
            instrument if item["type"] != "DEPOSIT" else None,
            item["type"],
            date.fromisoformat(item["date"]),
            **{key: value for key, value in item.items() if key not in {"type", "date"}},
        )
        for item in fixture["transactions"]
    ]
    state = ledger_state(rows, date(2025, 1, 6), datetime(2025, 2, 1, tzinfo=UTC))
    expected = {key: Decimal(value) for key, value in fixture["expected"].items()}
    position = state.positions[(account, instrument)]
    for field in ("quantity", "cost_basis", "average_cost", "realized_pnl"):
        assert getattr(position, field) == expected[field]
    assert state.cash[(account, "USD")] == expected["cash"]
    market_value = position.quantity * expected["closing_price"]
    assert market_value == expected["market_value"]
    assert market_value - position.cost_basis == expected["unrealized_pnl"]
    total = market_value + state.cash[(account, "USD")]
    assert total == expected["portfolio_value"]
    assert total * expected["valuation_fx"] == expected["portfolio_value_chf"]
    assert (
        total - sum((amount for _, _, amount in state.external_flows), Decimal(0))
        == expected["absolute_native_return"]
    )
    performance = fixture["performance"]
    assert twr_period(
        Decimal(performance["twr_opening"]),
        Decimal(performance["twr_ending"]),
        Decimal(performance["external_flow"]),
    ) == Decimal(performance["twr"])
    irr = xirr(
        [(date.fromisoformat(day), Decimal(amount)) for day, amount in performance["xirr_flows"]]
    )
    assert irr is not None and abs(irr - Decimal(performance["xirr"])) < Decimal("0.00000001")


@pytest.mark.parametrize(
    "flows",
    [
        [
            (date(2023, 1, 1), Decimal(-100)),
            (date(2024, 1, 1), Decimal(-100)),
            (date(2024, 12, 31), Decimal(231)),
        ],
        [
            (date(2023, 1, 1), Decimal(-100)),
            (date(2024, 1, 1), Decimal(50)),
            (date(2024, 12, 31), Decimal(66)),
        ],
    ],
)
def test_xirr_deposits_and_withdrawal(flows) -> None:
    result = xirr(flows)
    assert result is not None and abs(result - Decimal("0.1")) < Decimal("0.001")


def test_ambiguous_xirr_and_reverse_split() -> None:
    assert (
        xirr(
            [
                (date(2023, 1, 1), Decimal(-100)),
                (date(2024, 1, 1), Decimal(230)),
                (date(2024, 12, 31), Decimal(-132)),
            ]
        )
        is None
    )
    account, instrument = uuid4(), uuid4()
    rows = [
        make_row(account, instrument, "BUY", date(2025, 1, 2), quantity="100", price="10"),
        make_row(account, instrument, "SPLIT", date(2025, 1, 3), quantity="0.1"),
    ]
    state = ledger_state(rows, date(2025, 1, 3), datetime(2025, 2, 1, tzinfo=UTC))
    position = state.positions[(account, instrument)]
    assert position.quantity == Decimal(10) and position.cost_basis == Decimal(1000)
    assert position.average_cost == Decimal(100) and position.realized_pnl == 0


def test_negative_cash_and_fee_tax_interest() -> None:
    account, instrument = uuid4(), uuid4()
    day = date(2025, 1, 2)
    rows = [
        make_row(account, instrument, "BUY", day, quantity="10", price="100"),
        make_row(account, None, "INTEREST", day, amount="10", fee="1", tax="2"),
        make_row(account, None, "FEE", day, amount="3"),
        make_row(account, None, "TAX", day, amount="4"),
    ]
    state = ledger_state(rows, day, datetime(2025, 2, 1, tzinfo=UTC))
    assert state.cash[(account, "USD")] == Decimal(-1000)
    assert state.fees["USD"] == 4 and state.taxes["USD"] == 6 and state.income["USD"] == 10


def test_fx_attribution_includes_offsetting_native_cash_and_securities() -> None:
    class FakeFx:
        async def fx(self, *_args):
            return {"status": "AVAILABLE", "rate": Decimal(1)}

    service = PortfolioPerformanceService.__new__(PortfolioPerformanceService)
    service.valuation = SimpleNamespace(market=FakeFx())
    prior = {
        "cash": [{"currency": "USD", "amount": Decimal(-1000), "fx": {"rate": Decimal("0.9")}}],
        "holdings": [
            {
                "currency": "USD",
                "market_value_native": Decimal(1200),
                "fx": {"rate": Decimal("0.9")},
            }
        ],
    }
    effect = asyncio.run(
        service._opening_exposure_fx_effect(
            prior, date(2025, 1, 3), "CHF", datetime(2025, 2, 1, tzinfo=UTC)
        )
    )
    assert effect == Decimal(20)


@pytest.mark.parametrize(
    "kind,quantity,price,amount",
    [
        ("BUY", "1", None, None),
        ("SELL", "0", "10", None),
        ("DEPOSIT", None, None, None),
    ],
)
def test_invalid_persisted_ledger_never_becomes_zero(kind, quantity, price, amount) -> None:
    account, instrument = uuid4(), uuid4()
    row = make_row(
        account,
        instrument if kind != "DEPOSIT" else None,
        kind,
        date(2025, 1, 2),
        quantity=quantity,
        price=price,
        amount=amount,
    )
    with pytest.raises(AppError) as error:
        ledger_state([row], date(2025, 1, 2), datetime(2025, 2, 1, tzinfo=UTC))
    assert error.value.code == "INVALID_TRANSACTION"
