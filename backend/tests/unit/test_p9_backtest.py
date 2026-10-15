from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.backtesting.engine import run_backtest
from app.schemas.pit import BacktestInput, DatasetInput
from tests.unit.test_p6_golden_backtest import golden_dataset


def test_research_range_can_contain_required_strategy_oos_without_removing_resource_cap():
    data = {
        "universe_id": uuid4(),
        "benchmark_id": uuid4(),
        "start": "2021-01-01",
        "end": "2025-01-01",
    }
    assert DatasetInput.model_validate(data).availability_mode == "STRICT_PIT"
    with pytest.raises(ValidationError):
        DatasetInput.model_validate({**data, "start": "2018-01-01"})


def test_historical_no_change_portfolio_and_archived_signal_timing():
    config = BacktestInput(
        dataset_id=uuid4(), initial_capital="1000", commission="1", spread_bps=0, slippage_bps=0
    )
    initial = {"cash": "500", "positions": {"stock": "5"}}
    unchanged = run_backtest(golden_dataset(), config, initial_state=initial, execution_plans={})
    assert Decimal(unchanged["equity"][-1]["value"]) == 1050
    assert Decimal(unchanged["metrics"]["Total Return"]) == Decimal(".05")
    assert not unchanged["fills"]
    plan = {
        "before_cash": "500",
        "before_positions": {"stock": "5"},
        "targets": {"stock": "6"},
        "signal_generated_at": "2024-01-02T21:30:01+00:00",
        "information_cutoff_at": "2024-01-02T21:30:00+00:00",
    }
    result = run_backtest(
        golden_dataset(), config, initial_state=initial, execution_plans={"2024-01-02": plan}
    )
    assert len(result["fills"]) == 1
    assert result["fills"][0]["execution_price_timestamp"] > plan["signal_generated_at"]
    assert Decimal(result["equity"][-1]["value"]) == 1059
    assert Decimal(result["metrics"]["Transaction Costs"]) == 1
    plan["signal_generated_at"] = "2024-01-03T15:00:00+00:00"
    leaked = run_backtest(
        golden_dataset(), config, initial_state=initial, execution_plans={"2024-01-02": plan}
    )
    assert not leaked["fills"] and "ARCHIVED_SIGNAL_EXECUTION_UNAVAILABLE" in leaked["warnings"]
    plan["before_cash"] = "0"
    diverged = run_backtest(
        golden_dataset(), config, initial_state=initial, execution_plans={"2024-01-02": plan}
    )
    assert not diverged["fills"] and "HISTORICAL_PORTFOLIO_CONTEXT_DIVERGED" in diverged["warnings"]


def test_initial_state_cannot_double_apply_actions_or_claim_a_different_nav():
    config = BacktestInput(dataset_id=uuid4(), initial_capital="1000")
    initial = {"cash": "500", "positions": {"stock": "5"}}
    dataset = golden_dataset()
    dataset["actions"] = {
        "stock": [{"id": "split", "type": "SPLIT", "date": "2024-01-02", "ratio": "2"}]
    }
    result = run_backtest(dataset, config, initial_state=initial, execution_plans={})
    assert result["status"] == "REJECTED"
    assert "INITIAL_STATE_ACTION_ENTITLEMENT_UNAVAILABLE" in result["warnings"]
    dataset["actions"] = {}
    initial["cash"] = "400"
    result = run_backtest(dataset, config, initial_state=initial, execution_plans={})
    assert (
        result["status"] == "REJECTED" and "INITIAL_STATE_VALUATION_MISMATCH" in result["warnings"]
    )
