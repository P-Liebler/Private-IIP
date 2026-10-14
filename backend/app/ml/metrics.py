"""Statistical evaluation; no interpretation as investment profitability."""

from typing import Any

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(y: Any, probability: Any) -> dict[str, Any]:
    y, probability = np.asarray(y), np.asarray(probability, dtype=float)
    if (
        not len(y)
        or not np.isfinite(probability).all()
        or ((probability < 0) | (probability > 1)).any()
    ):
        raise ValueError("INVALID_EVALUATION_INPUT")
    predicted = probability >= 0.5
    curve = []
    ece = 0.0
    for i in range(10):
        mask = (probability >= i / 10) & (probability < (i + 1) / 10 if i < 9 else probability <= 1)
        count = int(mask.sum())
        if count:
            observed, expected = float(y[mask].mean()), float(probability[mask].mean())
            ece += count / len(y) * abs(observed - expected)
            curve.append({"bin": i, "count": count, "observed": observed, "predicted": expected})
    two_classes = len(np.unique(y)) == 2
    return {
        "sample_size": len(y),
        "class_balance": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, probability)) if two_classes else None,
        "pr_auc": float(average_precision_score(y, probability)) if two_classes else None,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "brier": float(brier_score_loss(y, probability)),
        "ece": ece,
        "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
        "calibration_curve": curve,
        "calibration_coverage": len(curve) / 10,
    }


def regression_metrics(y: Any, prediction: Any) -> dict[str, Any]:
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    if not len(y) or not np.isfinite(y).all() or not np.isfinite(prediction).all():
        raise ValueError("INVALID_EVALUATION_INPUT")
    correlatable = len(y) >= 3 and np.std(y) > 0 and np.std(prediction) > 0
    return {
        "sample_size": len(y),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(np.sqrt(mean_squared_error(y, prediction))),
        "bias": float(np.mean(prediction - y)),
        "pearson": float(pearsonr(y, prediction).statistic) if correlatable else None,
        "spearman": float(spearmanr(y, prediction).statistic) if correlatable else None,
    }


def block_bootstrap_brier(
    y: Any,
    probability: Any,
    dates: list[str],
    horizon: int,
    seed: int,
) -> dict[str, Any]:
    """Date clusters keep same-day instruments together; blocks span label horizon."""
    unique = sorted(set(dates))
    if len(unique) < horizon * 10:
        return {
            "status": "UNCERTAINTY_UNAVAILABLE",
            "distinct_dates": len(unique),
            "block_sessions": horizon,
        }
    losses = (np.asarray(y) - np.asarray(probability)) ** 2
    clustered = np.asarray([losses[np.asarray(dates) == day].mean() for day in unique])
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(200):
        starts = rng.integers(
            0, len(unique) - horizon + 1, size=int(np.ceil(len(unique) / horizon))
        )
        sampled = np.concatenate([clustered[s : s + horizon] for s in starts])[: len(unique)]
        estimates.append(float(sampled.mean()))
    low, high = np.quantile(estimates, [0.025, 0.975])
    return {
        "status": "AVAILABLE",
        "method": "moving-date-block-bootstrap-v1",
        "lower": float(low),
        "upper": float(high),
        "level": 0.95,
        "replicates": 200,
        "block_sessions": horizon,
        "distinct_dates": len(unique),
    }
