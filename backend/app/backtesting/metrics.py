from datetime import date
from decimal import Decimal
from statistics import stdev, variance
from typing import Any


def metrics(
    equity: list[dict[str, Any]],
    initial: Decimal,
    traded: Decimal,
    costs: Decimal,
    fills: int,
    risk_free_annual: Decimal | None,
    benchmark_values: list[Decimal] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        key: None
        for key in [
            "CAGR",
            "Sharpe",
            "Sortino",
            "Maximum Drawdown",
            "Volatility",
            "Alpha",
            "Beta",
            "Win Rate",
            "Total Return",
            "Benchmark Return",
            "Excess Return",
            "Turnover",
        ]
    }
    result.update(
        {
            "Transaction Costs": str(costs),
            "Number of Trades": fills,
            "risk_free_policy": "EXPLICIT_CONSTANT"
            if risk_free_annual is not None
            else "UNAVAILABLE",
            "minimum_ratio_returns": 20,
            "annualization_sessions": 252,
        }
    )
    if not equity or any(p.get("value") is None for p in equity):
        return {**result, "status": "INSUFFICIENT_DATA"}
    values = [Decimal(str(p["value"])) for p in equity]
    total = values[-1] / initial - 1
    peak = initial
    dd = Decimal(0)
    for v in values:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    result.update(
        {"Total Return": str(total), "Maximum Drawdown": str(dd), "Turnover": str(traded / initial)}
    )
    days = (date.fromisoformat(equity[-1]["date"]) - date.fromisoformat(equity[0]["date"])).days
    if days >= 365 and values[-1] > 0:
        result["CAGR"] = str((values[-1] / initial) ** (Decimal("365.25") / days) - 1)
    returns = [b / a - 1 for a, b in zip(values, values[1:], strict=False) if a > 0]
    if len(returns) >= 20:
        vol = stdev(returns)
        mean = sum(returns, Decimal(0)) / len(returns)
        result["Volatility"] = str(vol * Decimal(252).sqrt())
        result["Win Rate"] = str(Decimal(sum(r > 0 for r in returns)) / len(returns))
        if risk_free_annual is not None:
            rf = (1 + risk_free_annual) ** (Decimal(1) / 252) - 1
            excess = [r - rf for r in returns]
            if vol > 0:
                result["Sharpe"] = str((mean - rf) / vol * Decimal(252).sqrt())
            downside = (
                sum((min(r, Decimal(0)) ** 2 for r in excess), Decimal(0)) / len(excess)
            ).sqrt()
            if downside > 0:
                result["Sortino"] = str((mean - rf) / downside * Decimal(252).sqrt())
        if benchmark_values and len(benchmark_values) == len(values):
            br = [b / a - 1 for a, b in zip(benchmark_values, benchmark_values[1:], strict=False)]
            if variance(br) > 0:
                bm = sum(br, Decimal(0)) / len(br)
                cov = sum(
                    ((r - mean) * (b - bm) for r, b in zip(returns, br, strict=True)), Decimal(0)
                ) / (len(br) - 1)
                beta = cov / variance(br)
                result["Beta"] = str(beta)
                if risk_free_annual is not None:
                    result["Alpha"] = str(((mean - rf) - beta * (bm - rf)) * 252)
    if benchmark_values and len(benchmark_values) == len(values) and benchmark_values[0] > 0:
        br_total = benchmark_values[-1] / benchmark_values[0] - 1
        result["Benchmark Return"] = str(br_total)
        result["Excess Return"] = str(total - br_total)
    return {**result, "status": "AVAILABLE" if len(returns) >= 20 else "PARTIAL"}
