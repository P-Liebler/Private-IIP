import json

import numpy as np
import pytest

from app.ml.calibration import calibrated, fit_conformal, fit_platt
from app.ml.metrics import classification_metrics, regression_metrics
from app.ml.models import fit_estimator, fit_preprocessor, predict_estimator, transform
from app.ml.promotion import promotion_reasons
from app.ml.validation import FoldWindow


@pytest.mark.parametrize(
    "kind",
    [
        "LOGISTIC",
        "LINEAR",
        "LIGHTGBM_CLASSIFIER",
        "LIGHTGBM_REGRESSOR",
        "XGBOOST_CLASSIFIER",
        "XGBOOST_REGRESSOR",
    ],
)
def test_all_estimators_reproducible_data_only_roundtrip(kind):
    x = np.random.default_rng(71).normal(size=(200, 3))
    y = (x[:, 0] > 0).astype(int) if "CLASSIFIER" in kind or kind == "LOGISTIC" else x[:, 0] * 0.01
    model = fit_estimator(kind, x, y, 71)
    repeat = fit_estimator(kind, x, y, 71)
    assert model == repeat
    assert np.allclose(
        predict_estimator(model, x), predict_estimator(json.loads(json.dumps(model)), x)
    )


def test_train_only_scaling_and_critical_missing_gate():
    train = [[1.0, 2.0], [3.0, np.nan], [5.0, 4.0]]
    params = fit_preprocessor(train, ["critical", "optional"], ["critical"])
    original = json.dumps(params)
    transform([[1000.0, np.nan]], params)
    assert json.dumps(params) == original
    assert params["medians"] == [3.0, 3.0]
    with pytest.raises(ValueError, match="MISSING_CRITICAL"):
        transform([[np.nan, 5.0]], params)


def test_final_test_cannot_be_calibration_window():
    with pytest.raises(ValueError, match="CHRONOLOGICAL_WINDOWS"):
        FoldWindow(
            validation_start="2021-01-01T00:00:00Z",
            calibration_start="2023-01-01T00:00:00Z",
            test_start="2023-01-01T00:00:00Z",
            final_end="2024-01-01T00:00:00Z",
            embargo_sessions=90,
        )


def test_platt_and_small_sample_abstention():
    probability = np.linspace(0.01, 0.99, 200)
    y = (probability > 0.5).astype(int)
    fitted = fit_platt(probability, y)
    assert fitted["status"] == "AVAILABLE"
    assert np.isfinite(calibrated(probability, fitted)).all()
    assert fit_platt(probability[:10], y[:10])["status"] == "CALIBRATION_UNAVAILABLE"


def test_conformal_requires_independent_date_blocks():
    result = fit_conformal([0.1] * 500, [0.2] * 500, ["same-date"] * 500, 30)
    assert result["status"] == "INTERVAL_UNAVAILABLE"


def test_metric_goldens_and_undefined_correlation():
    result = classification_metrics([0, 1], [0.1, 0.9])
    assert result["brier"] == pytest.approx(0.01)
    assert result["roc_auc"] == 1
    assert result["confusion_matrix"] == [[1, 0], [0, 1]]
    result = regression_metrics([1, 1, 1], [2, 2, 2])
    assert result["mae"] == 1 and result["bias"] == 1
    assert result["pearson"] is None


@pytest.mark.parametrize(
    "field,reason",
    [
        ("synthetic_evidence", "SYNTHETIC_EVIDENCE_FORBIDDEN"),
        ("baseline_passed", "BASELINE_COMPARISON_FAILED"),
        ("calibration_passed", "CALIBRATION_FAILED"),
        ("interval_passed", "INTERVAL_COVERAGE_FAILED"),
    ],
)
def test_promotion_never_rescues_failed_gate(field, reason):
    evidence = {
        "production_data_eligible": True,
        "synthetic_evidence": False,
        "training_observations": 2000,
        "oos_observations": 1000,
        "oos_signal_dates": 1000,
        "folds": 3,
        **dict.fromkeys(
            [
                "leakage_verified",
                "baseline_passed",
                "calibration_passed",
                "interval_passed",
                "stability_passed",
                "financial_backtest_passed",
                "model_card_verified",
                "artifact_verified",
                "code_verified",
            ],
            True,
        ),
    }
    assert promotion_reasons(evidence) == []
    evidence[field] = True if field == "synthetic_evidence" else False
    assert reason in promotion_reasons(evidence)
