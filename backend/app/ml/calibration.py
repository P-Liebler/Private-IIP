"""Serializable Platt and split-conformal parameters from calibration only."""

from typing import Any

import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression


def fit_platt(probability: Any, y: Any) -> dict[str, Any]:
    y = np.asarray(y)
    if len(y) < 100 or len(np.unique(y)) != 2 or min(np.bincount(y.astype(int))) < 20:
        return {"status": "CALIBRATION_UNAVAILABLE", "method": "platt-v1", "sample_size": len(y)}
    scores = logit(np.clip(probability, 1e-8, 1 - 1e-8)).reshape(-1, 1)
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200, random_state=0).fit(scores, y)
    return {
        "status": "AVAILABLE",
        "method": "platt-v1",
        "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
        "sample_size": len(y),
    }


def calibrated(probability: Any, parameters: dict[str, Any]) -> Any:
    if parameters["status"] != "AVAILABLE":
        raise ValueError("CALIBRATION_UNAVAILABLE")
    return expit(
        parameters["coefficient"] * logit(np.clip(probability, 1e-8, 1 - 1e-8))
        + parameters["intercept"]
    )


def fit_conformal(
    y: Any,
    prediction: Any,
    dates: list[str],
    horizon: int,
    label_end_dates: list[str] | None = None,
) -> dict[str, Any]:
    """Use non-overlapping signal dates, with all instruments grouped by date.

    Block maximum residuals are conservative. Financial nonstationarity means
    this is empirical uncertainty, not an unconditional coverage guarantee.
    """
    unique = sorted(set(dates))
    chosen = unique[::horizon]
    if label_end_dates is not None:
        ends = {
            day: max(
                end for signal, end in zip(dates, label_end_dates, strict=True) if signal == day
            )
            for day in unique
        }
        chosen = []
        previous_end = ""
        for day in unique:
            if day > previous_end:
                chosen.append(day)
                previous_end = ends[day]
    if len(chosen) < 30:
        return {
            "status": "INTERVAL_UNAVAILABLE",
            "method": "date-block-conformal-v1",
            "interval_level": 0.8,
            "independent_date_blocks": len(chosen),
        }
    residuals = abs(np.asarray(y) - np.asarray(prediction))
    scores = [float(residuals[np.asarray(dates) == day].max()) for day in chosen]
    rank = int(np.ceil((len(scores) + 1) * 0.8))
    if rank > len(scores):
        return {"status": "INTERVAL_UNAVAILABLE", "method": "date-block-conformal-v1"}
    radius = sorted(scores)[rank - 1]
    return {
        "status": "AVAILABLE",
        "method": "date-block-conformal-v1",
        "radius": radius,
        "interval_level": 0.8,
        "independent_date_blocks": len(chosen),
        "empirical_calibration_coverage": float(np.mean(np.asarray(scores) <= radius)),
        "coverage_guarantee": "NOT_ASSUMED_FOR_NONSTATIONARY_MARKETS",
    }
