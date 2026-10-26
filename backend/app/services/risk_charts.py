"""Versioned display calculations from an immutable P8 snapshot, never current data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from app.services.fundamentals import digest

VERSION = "P8_PINNED_RETURN_CHARTS_V1"


def risk_chart_series(result: dict[str, Any]) -> dict[str, Any]:
    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "DATA_UNAVAILABLE",
            "reason": reason,
            "calculation_version": VERSION,
            "returns": [],
            "drawdown": [],
            "benchmark": [],
            "benchmark_status": "UNAVAILABLE",
        }

    if not result.get("quality", {}).get("complete_return_series"):
        return unavailable("INCOMPLETE_VERIFIED_RETURN_SERIES")
    observations = result.get("return_observations", [])
    if len(observations) < 2:
        return unavailable("INSUFFICIENT_RETURN_OBSERVATIONS")
    benchmark_id = (result.get("benchmark") or {}).get("instrument_id")
    benchmark_returns = result.get("asset_returns", {}).get(benchmark_id, {})
    returns, drawdowns, benchmark = [], [], []
    wealth, peak, benchmark_wealth = Decimal(1), Decimal(1), Decimal(1)
    benchmark_quality = result.get("asset_quality", {}).get(benchmark_id, {})
    benchmark_complete = bool(
        benchmark_id
        and benchmark_quality.get("coverage_id")
        and benchmark_quality.get("status") == "AVAILABLE"
    )
    previous = None
    try:
        with localcontext() as context:
            context.prec = 34
            for i, observation in enumerate(observations):
                day = date.fromisoformat(observation["date"])
                if previous is not None and day <= previous:
                    return unavailable("INVALID_RETURN_OBSERVATION_ORDER")
                previous = day
                if observation.get("status") != "AVAILABLE":
                    return unavailable("INVALID_RETURN_OBSERVATION")
                if i:
                    value = Decimal(str(observation["return"]))
                    if not value.is_finite():
                        return unavailable("INVALID_RETURN_OBSERVATION")
                    wealth *= 1 + value
                    benchmark_value = benchmark_returns.get(day.isoformat())
                    if benchmark_value is None:
                        benchmark_complete = False
                    elif benchmark_complete:
                        b = Decimal(str(benchmark_value))
                        if not b.is_finite():
                            benchmark_complete = False
                        else:
                            benchmark_wealth *= 1 + b
                peak = max(peak, wealth)
                returns.append({"date": day.isoformat(), "value": str(wealth - 1)})
                drawdowns.append({"date": day.isoformat(), "value": str(wealth / peak - 1)})
                benchmark.append({"date": day.isoformat(), "value": str(benchmark_wealth - 1)})
    except (KeyError, ValueError, TypeError, InvalidOperation, ZeroDivisionError):
        return unavailable("INVALID_RETURN_OBSERVATION")
    output = {
        "status": "AVAILABLE",
        "reason": None,
        "calculation_version": VERSION,
        "returns": returns,
        "drawdown": drawdowns,
        "benchmark": benchmark if benchmark_complete else [],
        "benchmark_status": "AVAILABLE" if benchmark_complete else "UNAVAILABLE",
    }
    return {**output, "derived_content_hash": digest(output)}
