from decimal import Decimal
from statistics import stdev, variance
from typing import Any

D = Decimal
RISK_VERSION = "portfolio-risk-v1:sample-252:historical-type7"
VAR_CONFIDENCE = D(".95")


def covariance(left: list[Decimal], right: list[Decimal]) -> Decimal:
    lm, rm = sum(left, D(0)) / len(left), sum(right, D(0)) / len(right)
    return sum(((a - lm) * (b - rm) for a, b in zip(left, right, strict=True)), D(0)) / (
        len(left) - 1
    )


def quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[min(lower + 1, len(ordered) - 1)] * weight


def historical_var(returns: list[Decimal], confidence: Decimal = VAR_CONFIDENCE) -> dict[str, Any]:
    if len(returns) < 252:
        return {
            "status": "VAR_UNAVAILABLE",
            "var": None,
            "cvar": None,
            "observations": len(returns),
            "minimum_observations": 252,
        }
    threshold = quantile(returns, 1 - confidence)
    tail = [r for r in returns if r <= threshold]
    return {
        "status": "AVAILABLE",
        "var": str(-threshold),
        "cvar": str(-sum(tail, D(0)) / len(tail)) if len(tail) >= 10 else None,
        "cvar_status": "AVAILABLE" if len(tail) >= 10 else "CVAR_UNAVAILABLE",
        "tail_sample_size": len(tail),
        "confidence": str(confidence),
        "observations": len(returns),
        "quantile": "TYPE_7_LINEAR",
        "sign_convention": "POSITIVE_LOSS_NEGATIVE_HISTORICAL_GAIN",
        "warning": "VaR is not a maximum possible loss.",
    }


def risk_metrics(
    dated_returns: list[tuple[str, Decimal]],
    benchmark: dict[str, Decimal],
    complete: bool,
    initial_date: str | None = None,
) -> dict[str, Any]:
    returns = [r for _, r in dated_returns]
    result: dict[str, Any] = {
        "rule_version": RISK_VERSION,
        "observations": len(returns),
        "daily_volatility": None,
        "annualized_volatility": None,
        "beta": None,
        "maximum_drawdown": None,
        "peak_date": None,
        "trough_date": None,
        "sample_start": dated_returns[0][0] if dated_returns else None,
        "sample_end": dated_returns[-1][0] if dated_returns else None,
        "status": "INSUFFICIENT_HISTORY",
        "var": {"status": "VAR_UNAVAILABLE", "var": None, "cvar": None},
        "variance_convention": "SAMPLE_DDOF_1",
        "annualization_sessions": 252,
    }
    if not complete:
        return {**result, "status": "INCOMPLETE_VALIDATED_RETURN_SERIES"}
    if (
        any(not r.is_finite() or r < -1 for r in returns)
        or dated_returns != sorted(dated_returns)
        or len({day for day, _ in dated_returns}) != len(dated_returns)
    ):
        return {**result, "status": "INVALID_RETURN_SERIES"}
    if len(returns) >= 20:
        vol = stdev(returns)
        result.update(
            {
                "status": "AVAILABLE",
                "daily_volatility": str(vol),
                "annualized_volatility": str(vol * D(252).sqrt()),
            }
        )
    if returns:
        level, peak, worst = D(1), D(1), D(0)
        peak_date = initial_date or dated_returns[0][0]
        for day, value in dated_returns:
            if value < -1:
                return {**result, "status": "INVALID_RETURN_SERIES"}
            level *= 1 + value
            if level > peak:
                peak, peak_date = level, day
            drawdown = level / peak - 1
            if drawdown < worst:
                worst = drawdown
                result["peak_date"], result["trough_date"] = peak_date, day
        result["maximum_drawdown"] = str(worst)
    aligned = [(value, benchmark[day]) for day, value in dated_returns if day in benchmark]
    result["beta_observations"] = len(aligned)
    if len(aligned) >= 60:
        own, other = [a for a, _ in aligned], [b for _, b in aligned]
        if variance(other) > 0:
            result["beta"] = str(covariance(own, other) / variance(other))
    result["beta_status"] = "AVAILABLE" if result["beta"] is not None else "BETA_UNAVAILABLE"
    result["var"] = historical_var(returns)
    return result


def correlations(
    series: dict[str, dict[str, Decimal]], window: int, reference_dates: list[str] | None = None
) -> dict[str, Any]:
    ids = sorted(series)
    cells = []
    for left in ids:
        for right in ids:
            expected = reference_dates[-window:] if reference_dates is not None else None
            dates = (
                [d for d in expected if d in series[left] and d in series[right]]
                if expected is not None
                else sorted(set(series[left]) & set(series[right]))[-window:]
            )
            a, b = [series[left][day] for day in dates], [series[right][day] for day in dates]
            value = None
            if len(dates) == window and len(dates) >= 30 and variance(a) > 0 and variance(b) > 0:
                value = covariance(a, b) / (stdev(a) * stdev(b))
            cells.append(
                {
                    "left": left,
                    "right": right,
                    "value": str(value) if value is not None else None,
                    "observations": len(dates),
                    "status": "AVAILABLE" if value is not None else "CORRELATION_UNAVAILABLE",
                }
            )
    return {
        "window_sessions": window,
        "instrument_ids": ids,
        "cells": cells,
        "policy": "EXACT_ALIGNED_VALID_TOTAL_RETURNS",
    }
