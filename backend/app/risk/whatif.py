"""Pure hypothetical positions/cash. This module cannot write ledger entries."""

from copy import deepcopy
from decimal import Decimal
from typing import Any

from app.core.errors import AppError
from app.risk.exposure import exposures, health, liquidity_score
from app.risk.statistics import correlations, risk_metrics

D = Decimal


def hypothetical(
    risk: dict[str, Any], config: dict[str, Any], quotes: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    value = deepcopy(risk["current_valuation"])
    if (
        value["status"] != "COMPLETE"
        or value["total_value_base"] is None
        or D(str(value["total_value_base"])) <= 0
    ):
        raise AppError(422, "WHATIF_DATA_UNAVAILABLE", "Complete valuation required")
    holdings, cash = value["holdings"], value["cash"]
    costs, executed = D(0), []
    for trade in config["trades"]:
        iid = str(trade["instrument_id"])
        quote = quotes.get(iid)
        if quote is None or quote.get("valuation_status") != "CURRENT":
            raise AppError(
                422, "WHATIF_QUOTE_UNAVAILABLE", "Validated current quote and FX required"
            )
        matching = [
            h for h in holdings if str(h["instrument_id"]) == iid and D(str(h["quantity"])) > 0
        ]
        cash_currency = trade.get("cash_currency") or value["base_currency"]
        # The hypothetical uses the existing account's cash; no implicit credit/FX trade.
        candidates = [c for c in cash if c["currency"] == cash_currency]
        if not candidates:
            raise AppError(
                422, "WHATIF_CASH_UNAVAILABLE", "Selected cash currency/account unavailable"
            )
        account = candidates[0]
        fx = account.get("fx", {})
        if fx.get("status") != "AVAILABLE" or fx.get("rate") is None:
            raise AppError(422, "WHATIF_FX_UNAVAILABLE", "Validated cash FX required")
        rate = D(str(fx["rate"]))
        if trade["side"] == "SELL":
            if not matching:
                raise AppError(422, "WHATIF_POSITION_UNAVAILABLE", "Cannot sell an unheld position")
            fraction = D(str(trade["sell_fraction"]))
            amount = sum((D(str(h["market_value_base"])) * fraction for h in matching), D(0))
        else:
            amount = D(str(trade["amount_base"]))
        fee = (
            D(str(config["commission_base"]))
            + amount * (D(str(config["spread_bps"])) + D(str(config["slippage_bps"]))) / 10000
        )
        if trade["side"] == "BUY":
            if D(str(account["base_amount"])) < amount + fee:
                raise AppError(
                    422,
                    "WHATIF_INSUFFICIENT_CASH",
                    "Hypothetical purchase exceeds available cash including fees",
                )
            native_rate = D(str(quote["fx"]["rate"]))
            price = D(str(quote["price"]))
            quantity = amount / (price * native_rate)
            destination = next(
                (h for h in matching if h["account_id"] == account["account_id"]), None
            )
            if destination is None:
                destination = deepcopy(quote)
                destination.update(
                    {
                        "account_id": account["account_id"],
                        "quantity": "0",
                        "market_value_base": "0",
                        "market_value_native": "0",
                    }
                )
                holdings.append(destination)
            destination["quantity"] = str(D(str(destination["quantity"])) + quantity)
            destination["market_value_base"] = str(
                D(str(destination["market_value_base"])) + amount
            )
            destination["market_value_native"] = str(
                D(str(destination["market_value_native"])) + amount / native_rate
            )
            cash_change = -amount - fee
        else:
            for holding in matching:
                for key in ("quantity", "market_value_base", "market_value_native"):
                    holding[key] = str(D(str(holding[key])) * (1 - fraction))
            cash_change = amount - fee
            if D(str(account["base_amount"])) + cash_change < 0:
                raise AppError(422, "WHATIF_INSUFFICIENT_CASH", "Fees exceed proceeds and cash")
        account["base_amount"] = str(D(str(account["base_amount"])) + cash_change)
        account["amount"] = str(D(str(account["amount"])) + cash_change / rate)
        costs += fee
        executed.append({**trade, "value_base": str(amount), "cost_base": str(fee)})
    holdings[:] = [h for h in holdings if D(str(h["quantity"])) > 0]
    total = D(str(value["total_value_base"])) - costs
    if total <= 0:
        raise AppError(422, "WHATIF_NONPOSITIVE_NAV", "Costs leave no positive hypothetical NAV")
    value["total_value_base"] = str(total)
    value["cash_value_base"] = str(sum((D(str(c["base_amount"])) for c in cash), D(0)))
    value["securities_value_base"] = str(
        sum((D(str(h["market_value_base"])) for h in holdings), D(0))
    )
    value["known_value_base"] = str(total)
    value["accounting_analytics_status"] = "NOT_CALCULATED_FOR_HYPOTHETICAL"
    for holding in holdings:
        holding["weight"] = str(D(str(holding["market_value_base"])) / total)
        for key in list(holding):
            if "cost_basis" in key or "pnl" in key or key == "average_cost_native":
                holding[key] = None
    for key in list(value):
        if "cost_basis" in key or "pnl" in key:
            value[key] = None
    exposure = exposures(holdings, cash, total)
    # Constant proposed weights replayed on pinned history: explicitly pro forma,
    # never mislabeled as the portfolio's actual historical returns.
    dates = [o["date"] for o in risk["return_observations"][1:]]
    series = {
        iid: {d: D(str(r)) for d, r in returns.items()}
        for iid, returns in risk.get("asset_returns", {}).items()
    }
    returns, complete = [], bool(dates) and total > 0
    for day in dates:
        result = D(0)
        valid = True
        for holding in holdings:
            observed = series.get(str(holding["instrument_id"]), {}).get(day)
            if observed is None:
                valid = False
            else:
                result += D(str(holding["market_value_base"])) / total * D(str(observed))
        for account in cash:
            if account["currency"] != value["base_currency"] and D(str(account["amount"])) != 0:
                fx_return = risk.get("cash_fx_returns", {}).get(account["currency"], {}).get(day)
                if fx_return is None:
                    valid = False
                else:
                    result += D(str(account["base_amount"])) / total * D(str(fx_return))
        if valid:
            returns.append((day, result))
        else:
            complete = False
    benchmark = risk.get("benchmark")
    metrics = risk_metrics(
        returns,
        series.get(benchmark["instrument_id"], {}) if benchmark else {},
        complete,
        risk["return_observations"][0]["date"] if risk["return_observations"] else None,
    )
    quality_items = {
        q["instrument_id"]: q for q in risk.get("security_quality", {}).get("inputs", [])
    }
    quality_sum, security_total, quality_complete = D(0), D(0), bool(holdings)
    for holding in holdings:
        score = quality_items.get(str(holding["instrument_id"]), {}).get("quality", {})
        amount = D(str(holding["market_value_base"]))
        security_total += amount
        if score.get("status") != "AVAILABLE" or score.get("score") is None:
            quality_complete = False
        else:
            quality_sum += D(str(score["score"])) * amount
    quality = {
        "score": str(quality_sum / security_total)
        if quality_complete and security_total > 0
        else None,
        "inputs": quality_items,
        "policy": "REWEIGHT_SAME_PINNED_P5_QUALITY",
    }
    liquidity = liquidity_score(holdings, risk.get("liquidity_evidence", {}))
    return {
        "status": "AVAILABLE" if metrics["status"] == "AVAILABLE" else "PARTIAL",
        "hypothetical": True,
        "policy": "CONSTANT_PROPOSED_WEIGHTS_PINNED_HISTORY_NO_LEDGER_MUTATION-v1",
        "current_valuation": value,
        "metrics": metrics,
        "exposures": exposure,
        "health": health(exposure, metrics, quality, value["base_currency"], liquidity),
        "correlations": {
            str(w): correlations(
                {
                    str(h["instrument_id"]): series.get(str(h["instrument_id"]), {})
                    for h in holdings
                },
                w,
                dates,
            )
            for w in (30, 90, 252)
        },
        "asset_returns": risk.get("asset_returns", {}),
        "position_beta": {
            str(h["instrument_id"]): risk_metrics(
                sorted((d, D(str(r))) for d, r in series.get(str(h["instrument_id"]), {}).items()),
                series.get(benchmark["instrument_id"], {}) if benchmark else {},
                bool(dates) and len(series.get(str(h["instrument_id"]), {})) == len(dates),
            )
            for h in holdings
        },
        "benchmark": benchmark,
        "costs_base": str(costs),
        "trades": executed,
        "before": {k: risk[k] for k in ("metrics", "exposures", "health", "correlations")},
        "missing_inputs": [] if complete else ["COMPLETE_ALIGNED_ASSET_AND_CASH_FX_HISTORY"],
        "warning": "Hypothetical fixed-weight history assumes rebalancing; "
        "it is not realized performance.",
    }
