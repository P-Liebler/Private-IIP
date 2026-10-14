from decimal import Decimal
from statistics import stdev
from typing import Any

FEATURE_VERSION = "features-v1:raw-explicit-actions"
D = Decimal


def feature(
    value: Decimal | None, inputs: list[str], reason: str = "INSUFFICIENT_HISTORY"
) -> dict[str, Any]:
    return {
        "value": str(value) if value is not None else None,
        "missing_flag": value is None,
        "quality": "AVAILABLE" if value is not None else "FEATURE_UNAVAILABLE",
        "reason": None if value is not None else reason,
        "inputs": inputs,
    }


def ema(values: list[Decimal], period: int) -> list[Decimal]:
    if len(values) < period:
        return []
    result = [sum(values[:period], D(0)) / period]
    alpha = D(2) / (period + 1)
    for value in values[period:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def technical_features(
    prices: list[dict[str, Any]],
    total_return_closes: list[Decimal] | None,
    expected_sessions: list[str],
    benchmark: list[Decimal] | None = None,
) -> dict[str, Any]:
    """Contiguous session windows only. Decimal calculations, SMA-seeded EMAs."""
    ids = [str(p["id"]) for p in prices]
    names = [f"return_{n}d" for n in (1, 5, 20, 60, 120, 252)] + [
        f"momentum_{n}d" for n in (20, 60, 120)
    ]
    names += [
        "RSI",
        "MACD",
        "SMA20",
        "SMA50",
        "SMA200",
        "distance_SMA50",
        "distance_SMA200",
        "ATR",
        "volatility_20",
        "volatility_60",
        "volatility_252",
        "max_drawdown",
        "volume_change",
        "volume_zscore",
        "relative_strength",
    ]
    out = {name: feature(None, ids) for name in names}
    if not prices:
        return out
    # Cut at the most recent gap; never silently use a shorter calendar window.
    dates = [str(p["date"]) for p in prices]
    if dates != expected_sessions[-len(dates) :]:
        return {name: feature(None, ids, "MISSING_SESSION") for name in names}
    if total_return_closes is None or len(total_return_closes) != len(prices):
        return {name: feature(None, ids, "CORPORATE_ACTION_COVERAGE_UNVERIFIED") for name in names}
    x = total_return_closes
    for n in (1, 5, 20, 60, 120, 252):
        if len(x) > n:
            out[f"return_{n}d"] = feature(x[-1] / x[-1 - n] - 1, ids[-n - 1 :])
            if n in (20, 60, 120):
                out[f"momentum_{n}d"] = out[f"return_{n}d"]
    for n in (20, 50, 200):
        if len(x) >= n:
            sma = sum(x[-n:], D(0)) / n
            out[f"SMA{n}"] = feature(sma, ids[-n:])
            if n in (50, 200):
                out[f"distance_SMA{n}"] = feature(x[-1] / sma - 1, ids[-n:])
    if len(x) >= 15:
        diffs = [b - a for a, b in zip(x, x[1:], strict=False)]
        gain = sum((max(v, D(0)) for v in diffs[:14]), D(0)) / 14
        loss = sum((max(-v, D(0)) for v in diffs[:14]), D(0)) / 14
        for v in diffs[14:]:
            gain = (gain * 13 + max(v, D(0))) / 14
            loss = (loss * 13 + max(-v, D(0))) / 14
        rsi = (
            D(100)
            if loss == 0 and gain > 0
            else D(50)
            if loss == gain == 0
            else 100 - 100 / (1 + gain / loss)
        )
        out["RSI"] = feature(rsi, ids)
    if len(x) >= 26:
        out["MACD"] = feature(ema(x, 12)[-1] - ema(x, 26)[-1], ids)
    returns = [b / a - 1 for a, b in zip(x, x[1:], strict=False)]
    for n in (20, 60, 252):
        if len(returns) >= n:
            out[f"volatility_{n}"] = feature(stdev(returns[-n:]) * D(252).sqrt(), ids[-n - 1 :])
    if len(x) >= 2:
        peak = x[0]
        drawdown = D(0)
        for v in x:
            peak = max(peak, v)
            drawdown = min(drawdown, v / peak - 1)
        out["max_drawdown"] = feature(drawdown, ids)
    # High/low must be from the same split basis as close. Derive the scale per bar.
    if len(prices) >= 15 and all(
        p.get("high") is not None and p.get("low") is not None for p in prices
    ):
        ranges = []
        for i, p in enumerate(prices[1:], 1):
            scale = x[i] / D(str(p["close"]))
            high = D(str(p["high"])) * scale
            low = D(str(p["low"])) * scale
            ranges.append(max(high - low, abs(high - x[i - 1]), abs(low - x[i - 1])))
        atr = sum(ranges[:14], D(0)) / 14
        for v in ranges[14:]:
            atr = (atr * 13 + v) / 14
        out["ATR"] = feature(atr, ids)
    volumes = [D(str(p["volume"])) for p in prices if p.get("volume") is not None]
    if len(volumes) == len(prices):
        if len(volumes) >= 2 and volumes[-2] > 0:
            out["volume_change"] = feature(volumes[-1] / volumes[-2] - 1, ids[-2:])
        if len(volumes) >= 20 and stdev(volumes[-20:]) > 0:
            out["volume_zscore"] = feature(
                (volumes[-1] - sum(volumes[-20:], D(0)) / 20) / stdev(volumes[-20:]), ids[-20:]
            )
    if benchmark and len(benchmark) == len(x) and len(x) > 20:
        out["relative_strength"] = feature(
            x[-1] / x[-21] - benchmark[-1] / benchmark[-21], ids[-21:]
        )
    return out
