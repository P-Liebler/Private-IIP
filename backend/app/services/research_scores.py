"""Absolute research rubric, not a market percentile or a recommendation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

SCORE_RULE = "absolute-rubric-v1"
# Input, weight, zero-score boundary, full-score boundary. No reweighting missing inputs.
RUBRICS = {
    "Quality": [
        ("ROIC", "0.4", "0", "0.2"),
        ("fcf_margin", "0.3", "0", "0.25"),
        ("debt_to_equity", "0.3", "3", "0"),
    ],
    "Growth": [
        ("revenue_growth_yoy", "0.4", "-0.1", "0.2"),
        ("eps_growth_yoy", "0.3", "-0.1", "0.2"),
        ("fcf_growth_yoy", "0.3", "-0.1", "0.2"),
    ],
    "Value": [("Earnings Yield", "0.5", "0", "0.1"), ("FCF Yield", "0.5", "0", "0.1")],
    "Momentum": [("momentum_252d", "1", "-0.2", "0.3")],
    "Stability": [("margin_stability", "1", "0", "1")],
}


def calculate_scores(
    inputs: dict[str, dict[str, Any]], as_of: str, rule: str = SCORE_RULE
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name, rubric in RUBRICS.items():
        drivers: list[dict[str, Any]] = []
        missing: list[str] = []
        coverage, total = Decimal(0), Decimal(0)
        for metric, weight, low, high in rubric:
            w, lo, hi = Decimal(weight), Decimal(low), Decimal(high)
            data = inputs.get(metric, {})
            if data.get("status") != "AVAILABLE" or data.get("value") is None:
                missing.append(metric)
                continue
            number = Decimal(str(data["value"]))
            scaled = min(Decimal(1), max(Decimal(0), (number - lo) / (hi - lo)))
            contribution = scaled * w * 100
            drivers.append(
                {
                    "metric": metric,
                    "input": str(number),
                    "weight": weight,
                    "zero_boundary": low,
                    "full_boundary": high,
                    "contribution": str(contribution),
                    "provenance": data,
                }
            )
            coverage += w
            total += contribution
        results[name] = {
            "score": str(total) if not missing else None,
            "status": "AVAILABLE" if not missing else "INSUFFICIENT_DATA",
            "coverage": str(coverage),
            "drivers": drivers,
            "missing_inputs": missing,
            "rule_version": rule,
            "as_of": as_of,
            "method": "Absolute fixed rubric; no peer-universe percentile",
        }
    return results
