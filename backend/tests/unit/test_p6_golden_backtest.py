from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest

from app.backtesting.engine import run_backtest
from app.schemas.pit import BacktestInput


def golden_dataset() -> dict:
    """Declared synthetic: independent expected value = 9.99 * 110 = 1098.90."""
    days = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    market = {}
    rows = []
    for index, day in enumerate(days):
        bar = {
            "id": f"price-{index}",
            "raw_ingestion_id": f"raw-{index}",
            "open": "100",
            "close": "110" if index == 3 else "100",
            "currency": "USD",
            "fx": "1",
            "fx_provenance": {"derived": "IDENTITY"},
            "is_session": True,
            "open_timestamp": day + "T14:30:00+00:00",
            "close_timestamp": day + "T21:00:00+00:00",
            "information_cutoff_at": day + "T21:30:00+00:00",
            "signal_generated_at": day + "T21:30:01+00:00",
            "next_session": days[index + 1] if index < 3 else "2024-01-08",
            "next_open_timestamp": (days[index + 1] if index < 3 else "2024-01-08")
            + "T14:30:00+00:00",
        }
        market[day] = {"stock": bar, "benchmark": dict(bar)}
        rows.append(
            {
                "date": day,
                "instrument_id": "stock",
                "eligible": True,
                "features": {
                    "momentum_120d": {"value": "0.1", "missing_flag": False},
                    "quality_value": {"value": "70", "missing_flag": False},
                },
            }
        )
    return {
        "configuration": {"benchmark_id": "benchmark", "availability_mode": "STRICT_PIT"},
        "market": market,
        "rows": rows,
        "actions": {},
        "quality": {"excluded_observations": 0},
    }


@pytest.mark.parametrize(
    "strategy", ["EQUAL_WEIGHT", "MOMENTUM", "QUALITY_VALUE", "BENCHMARK_ONLY"]
)
def test_golden_cash_positions_costs_equity_drawdown_turnover(strategy: str) -> None:
    config = BacktestInput(
        dataset_id=uuid4(),
        strategy=strategy,
        initial_capital="1000",
        commission="1",
        spread_bps="0",
        slippage_bps="0",
    )
    result = run_backtest(golden_dataset(), config)
    assert result["status"] == "STRICT_PIT_VALID"
    assert Decimal(result["cash"]) == 0
    assert Decimal(next(iter(result["positions"].values()))) == Decimal("9.99")
    assert len(result["orders"]) == len(result["fills"]) == 1
    assert Decimal(result["equity"][-1]["value"]) == Decimal("1098.90")
    assert Decimal(result["metrics"]["Total Return"]) == Decimal("0.0989")
    assert Decimal(result["metrics"]["Transaction Costs"]) == 1
    assert Decimal(result["metrics"]["Turnover"]) == Decimal("0.999")
    assert Decimal(result["metrics"]["Maximum Drawdown"]) == Decimal("-0.001")
    assert result["metrics"]["Sharpe"] is None
    assert (
        result["fills"][0]["execution_price_timestamp"] > result["fills"][0]["signal_generated_at"]
    )
    assert result == run_backtest(golden_dataset(), config)


def test_no_same_close_and_missing_execution_or_fx() -> None:
    config = BacktestInput(dataset_id=uuid4(), initial_capital="1000")
    for mutation in ("open", "fx", "open_timestamp"):
        dataset = golden_dataset()
        dataset["market"]["2024-01-03"]["stock"][mutation] = (
            None if mutation != "open_timestamp" else "2024-01-02T21:00:00+00:00"
        )
        result = run_backtest(dataset, config)
        assert not result["fills"] and result["status"] == "INCOMPLETE"
        assert Decimal(result["cash"]) == 1000


def test_spread_slippage_and_zero_cost_comparison() -> None:
    dataset = golden_dataset()
    zero = BacktestInput(
        dataset_id=uuid4(),
        initial_capital="1000",
        commission=0,
        spread_bps=0,
        slippage_bps=0,
        zero_cost_comparison=True,
    )
    assert Decimal(run_backtest(dataset, zero)["equity"][-1]["value"]) == 1100
    costly = zero.model_copy(update={"spread_bps": Decimal(10), "slippage_bps": Decimal(10)})
    assert Decimal(run_backtest(dataset, costly)["equity"][-1]["value"]) < 1100
    assert Decimal(run_backtest(dataset, costly)["metrics"]["Transaction Costs"]) > 0


def test_split_dividend_cash_once_and_missing_valuation() -> None:
    dataset = golden_dataset()
    for day in ["2024-01-04", "2024-01-05"]:
        dataset["market"][day]["stock"]["close"] = "50"
    dataset["actions"] = {
        "stock": [
            {"id": "split", "date": "2024-01-04", "type": "SPLIT", "ratio": "2"},
            {
                "id": "dividend",
                "date": "2024-01-05",
                "type": "DIVIDEND",
                "cash_amount": "1",
                "currency": "USD",
                "payment_date": "2024-01-05",
            },
        ]
    }
    config = BacktestInput(
        dataset_id=uuid4(),
        initial_capital="1000",
        commission=0,
        spread_bps=0,
        slippage_bps=0,
        zero_cost_comparison=True,
    )
    r = run_backtest(dataset, config)
    assert Decimal(r["positions"]["stock"]) == 20 and Decimal(r["cash"]) == 20
    assert Decimal(r["equity"][-1]["value"]) == 1020
    broken = deepcopy(dataset)
    broken["market"]["2024-01-05"].pop("stock")
    assert run_backtest(broken, config)["equity"][-1]["value"] is None


def test_empty_membership_exits_at_next_session_with_costs() -> None:
    dataset = golden_dataset()
    dataset["rows"] = [r for r in dataset["rows"] if r["date"] <= "2024-01-03"]
    config = BacktestInput(
        dataset_id=uuid4(),
        initial_capital="1000",
        commission="1",
        spread_bps=0,
        slippage_bps=0,
        rebalance_sessions=1,
    )
    result = run_backtest(dataset, config)
    assert [fill["side"] for fill in result["fills"]] == ["BUY", "SELL"]
    assert Decimal(result["cash"]) == 998
    assert Decimal(result["positions"]["stock"]) == 0
    assert Decimal(result["metrics"]["Transaction Costs"]) == 2


def test_sell_fee_cannot_create_margin_cash() -> None:
    dataset = golden_dataset()
    dataset["rows"] = [r for r in dataset["rows"] if r["date"] <= "2024-01-03"]
    for day in ("2024-01-04", "2024-01-05"):
        dataset["market"][day]["stock"]["open"] = "0.00001"
        dataset["market"][day]["stock"]["close"] = "0.00001"
    config = BacktestInput(
        dataset_id=uuid4(),
        initial_capital="1000",
        commission="1",
        spread_bps=0,
        slippage_bps=0,
        rebalance_sessions=1,
    )
    result = run_backtest(dataset, config)
    assert Decimal(result["cash"]) == 0
    assert "INSUFFICIENT_CASH_FOR_COMMISSION" in result["warnings"]
    assert len(result["fills"]) == 1
