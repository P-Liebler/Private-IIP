from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.backtesting.engine import run_backtest
from app.ml.financial import financial_evaluation
from app.ml.promotion import PROMOTION_RULES, promotion_reasons
from app.ml.regimes import evaluate_regimes
from app.schemas.pit import BacktestInput
from app.schemas.validation import ExperimentInput, ReadinessInput, RegimeRule
from app.services.real_data_readiness import readiness_status
from tests.unit.test_p6_golden_backtest import golden_dataset


def test_regime_assignment_uses_only_pinned_features_and_requires_evidence():
    rule = RegimeRule(
        name="bull_market",
        feature="benchmark.momentum_20d",
        definition="Positive pinned benchmark momentum at signal time",
        comparison="GT",
        threshold="0",
    )
    rows = [
        {"date": f"2024-01-{i % 28 + 1:02d}", "features": {}, "target": {"classification": 1}}
        for i in range(60)
    ]
    evaluation = {
        "folds": [{"oos_predictions": [{"row_id": str(i), "prediction": 0.9} for i in range(60)]}]
    }
    result = evaluate_regimes(rows, evaluation, "classification", [rule])
    assert result["regimes"][0]["unknown_regime_observations"] == 60
    assert result["regimes"][0]["metrics"] is None
    for row in rows:
        row["features"] = {rule.feature: {"value": "0.1", "missing_flag": False}}
    result = evaluate_regimes(rows, evaluation, "classification", [rule])
    assert result["regimes"][0]["sample_size"] == 60
    assert result["regimes"][0]["status"] == "INSUFFICIENT_REGIME_EVIDENCE"
    assert result["comprehensive_robustness"] == "NOT_ESTABLISHED"
    with pytest.raises(ValidationError):
        RegimeRule(**{**rule.model_dump(), "feature": "target.excess_return"})
    body = protocol([uuid4(), uuid4()])
    body["regime_rules"] = [rule.model_dump(mode="json")] * 2
    with pytest.raises(ValidationError):
        ExperimentInput.model_validate(body)


@pytest.mark.parametrize(
    "reason,status",
    [
        ("SOURCE_APPROVAL_REQUIRED", "SOURCE_APPROVAL_REQUIRED"),
        ("SYNTHETIC_OR_UNVERIFIED_INPUTS", "BLOCKED_BY_REAL_DATA"),
        ("DATASET_REQUIRED", "BLOCKED_BY_REAL_DATA"),
        ("CORPORATE_ACTION_COVERAGE_MISSING", "CORPORATE_ACTION_COVERAGE_MISSING"),
        ("HISTORICAL_MEMBERSHIP_MISSING", "HISTORICAL_MEMBERSHIP_MISSING"),
        ("INSUFFICIENT_HISTORY", "INSUFFICIENT_HISTORY"),
        ("INSUFFICIENT_OOS", "INSUFFICIENT_OOS"),
        ("FX_COVERAGE_MISSING", "PARTIAL_REAL_DATA"),
    ],
)
def test_readiness_reports_specific_hard_blockers(reason, status):
    assert readiness_status([reason], "STRICT_PIT") == status


def candidate(dataset_id, model="LOGISTIC", target="classification", horizon=30):
    return {
        "dataset_id": str(dataset_id),
        "model_type": model,
        "target": target,
        "feature_names": ["momentum_20d"],
        "required_features": ["momentum_20d"],
        "horizon": horizon,
        "folds": [
            {
                "validation_start": "2020-01-02T00:00:00Z",
                "calibration_start": "2021-01-04T00:00:00Z",
                "test_start": "2023-01-03T00:00:00Z",
                "final_end": "2025-01-01T00:00:00Z",
                "embargo_sessions": horizon,
            }
        ],
    }


def protocol(ids):
    return {
        "name": "SYNTHETIC protocol contract",
        "rationale": "Controlled technical test, no real financial validation.",
        "source_policy": [{"source_slug": "MANUAL_CSV", "use": "manual_upload"}],
        "candidates": [
            candidate(ids[0]),
            candidate(ids[0], "LINEAR", "excess_return"),
            candidate(ids[1], horizon=90),
            candidate(ids[1], "LINEAR", "excess_return", 90),
        ],
    }


@pytest.mark.parametrize(
    "mutation",
    ["missing_horizon", "missing_target", "reused_fold", "small_embargo", "shuffled_windows"],
)
def test_protocol_rejects_invalid_or_leaking_experiment(mutation):
    body = protocol([uuid4(), uuid4()])
    if mutation == "missing_horizon":
        body["candidates"] = body["candidates"][:2]
    elif mutation == "missing_target":
        body["candidates"].pop(1)
    elif mutation == "reused_fold":
        for item in body["candidates"]:
            item["folds"].append(deepcopy(item["folds"][0]))
    elif mutation == "small_embargo":
        body["candidates"][2]["folds"][0]["embargo_sessions"] = 30
    else:
        body["candidates"][0]["folds"][0]["calibration_start"] = "2019-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        ExperimentInput.model_validate(body)


def test_readiness_never_counts_reconstructed_as_real_or_reduces_rules():
    assert readiness_status([], "RECONSTRUCTED_HISTORICAL") == "RECONSTRUCTED_RESEARCH_ONLY"
    assert PROMOTION_RULES["minimum_training_observations"] == 1000
    assert PROMOTION_RULES["minimum_oos_observations"] == 500
    assert PROMOTION_RULES["minimum_oos_signal_dates"] == 600
    assert PROMOTION_RULES["minimum_folds"] == 3
    assert "SYNTHETIC_EVIDENCE_FORBIDDEN" in promotion_reasons({"synthetic_evidence": True})


def test_audit_rejects_overlapping_partitions():
    fold = candidate(uuid4())["folds"][0]
    with pytest.raises(ValidationError):
        ReadinessInput(
            universe_id=uuid4(),
            benchmark_id=uuid4(),
            start="2018-01-01",
            end="2025-01-01",
            source_policy=[{"source_slug": "MANUAL_CSV", "use": "manual_upload"}],
            folds=[fold, fold],
        )


@pytest.mark.parametrize("currency,cost_bps", [("USD", "10"), ("CHF", "10"), ("USD", "0")])
def test_explicit_fx_execution_costs_and_cash_are_not_double_counted(currency, cost_bps):
    dataset = golden_dataset()
    dataset["configuration"]["base_currency"] = "CHF"
    for bars in dataset["market"].values():
        for bar in bars.values():
            bar["currency"] = currency
    config = BacktestInput(
        dataset_id=uuid4(),
        initial_capital="1000",
        commission="1",
        spread_bps="0",
        slippage_bps="0",
        fx_cost_bps=cost_bps,
    )
    result = run_backtest(dataset, config)
    fill = result["fills"][0]
    fee = Decimal(cost_bps) / 10000 if currency == "USD" else Decimal(0)
    quantity = Decimal(999) / (Decimal(100) * (1 + fee))
    assert Decimal(fill["quantity"]) == quantity
    assert Decimal(fill["fx_cost"]) == quantity * Decimal(100) * fee
    assert Decimal(result["metrics"]["Transaction Costs"]) == Decimal(1) + Decimal(fill["fx_cost"])
    assert Decimal(result["cash"]) == 0


def test_financial_evaluation_reuses_cost_engine_and_all_baselines():
    data = golden_dataset()
    data["configuration"].update(base_currency="CHF")
    data["quality"].update(total_observations=4, valid_observations=4)
    dataset = SimpleNamespace(
        id=uuid4(),
        configuration=data["configuration"],
        rows=data["rows"],
        manifest={"market": data["market"], "actions": data["actions"]},
        quality=data["quality"],
    )
    evaluation = {
        "folds": [
            {
                "window": {
                    "test_start": "2024-01-02T00:00:00Z",
                    "final_end": "2024-01-05T23:59:00Z",
                },
                "oos_predictions": [{"row_id": str(i), "prediction": 0.1} for i in range(4)],
            }
        ]
    }
    result = financial_evaluation(dataset, evaluation, 30)
    assert set(result["folds"][0]["baselines"]) == {
        "NO_CHANGE",
        "BENCHMARK_ONLY",
        "EQUAL_WEIGHT",
        "MOMENTUM",
        "QUALITY_VALUE",
    }
    assert result["folds"][0]["baselines"]["NO_CHANGE"]["metrics"]["Total Return"] == "0"
    assert result["passed"] is False
