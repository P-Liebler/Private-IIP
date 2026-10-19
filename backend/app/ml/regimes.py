"""Apply pre-registered rules only to pinned point-in-time OOS features."""

from decimal import Decimal
from typing import Any

import numpy as np

from app.ml.metrics import classification_metrics, regression_metrics
from app.ml.readiness import finite_feature
from app.schemas.validation import RegimeRule


def evaluate_regimes(
    rows: list[dict[str, Any]], evaluation: dict[str, Any], target: str, rules: list[RegimeRule]
) -> dict[str, Any]:
    output = []
    for rule in rules:
        selected, unknown = [], 0
        for fold in evaluation["folds"]:
            for prediction in fold["oos_predictions"]:
                row = rows[int(prediction["row_id"])]
                feature = row["features"].get(rule.feature, {})
                if feature.get("missing_flag", True) or not finite_feature(feature.get("value")):
                    unknown += 1
                    continue
                value = Decimal(str(feature["value"]))
                if (
                    (value > rule.threshold)
                    if rule.comparison == "GT"
                    else (value <= rule.threshold)
                ):
                    selected.append((row, prediction))
        dates = {row["date"] for row, _ in selected}
        sufficient = len(selected) >= 50 and len(dates) >= 30
        metrics = None
        if sufficient:
            y = np.asarray([float(row["target"][target]) for row, _ in selected])
            forecast = np.asarray([float(prediction["prediction"]) for _, prediction in selected])
            metrics = (
                classification_metrics(y, forecast)
                if target == "classification"
                else regression_metrics(y, forecast)
            )
        output.append(
            {
                "rule": rule.model_dump(mode="json"),
                "sample_size": len(selected),
                "distinct_signal_dates": len(dates),
                "unknown_regime_observations": unknown,
                "status": "OBSERVED_RESEARCH_RESULTS"
                if sufficient
                else "INSUFFICIENT_REGIME_EVIDENCE",
                "metrics": metrics,
            }
        )
    return {
        "contract": "pinned-oos-regime-feature-rules-v1",
        "regimes": output,
        "comprehensive_robustness": "NOT_ESTABLISHED"
        if len(output) < 6 or any(r["status"] != "OBSERVED_RESEARCH_RESULTS" for r in output)
        else "OBSERVED_TESTED_RULES_ONLY",
        "dependence": "Correlated date clusters; no independence or future-regime guarantee",
    }
