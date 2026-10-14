"""Explicit hypotheses; never price forecasts or trading instructions."""

from decimal import Decimal
from typing import Any

D = Decimal
SCENARIO_VERSION = "scenario-v1"
SCENARIOS = [
    (
        "sp500-minus10-v1",
        "S&P 500 −10%",
        {"calculation_type": "BETA_BASED_MARKET_SHOCK", "shock": "-.10", "market": "SP500"},
    ),
    (
        "sp500-minus20-v1",
        "S&P 500 −20%",
        {"calculation_type": "BETA_BASED_MARKET_SHOCK", "shock": "-.20", "market": "SP500"},
    ),
    (
        "nasdaq-minus20-v1",
        "NASDAQ −20%",
        {"calculation_type": "BETA_BASED_MARKET_SHOCK", "shock": "-.20", "market": "NASDAQ"},
    ),
    (
        "technology-minus25-v1",
        "Technology −25%",
        {"calculation_type": "DIRECT_POSITION_SHOCK", "shock": "-.25", "sector": "Technology"},
    ),
    (
        "usdchf-minus10-v1",
        "USD/CHF −10%",
        {
            "calculation_type": "CURRENCY_TRANSLATION_SHOCK",
            "shock": "-.10",
            "currency": "USD",
            "quote_currency": "CHF",
        },
    ),
    (
        "eurchf-minus10-v1",
        "EUR/CHF −10%",
        {
            "calculation_type": "CURRENCY_TRANSLATION_SHOCK",
            "shock": "-.10",
            "currency": "EUR",
            "quote_currency": "CHF",
        },
    ),
    (
        "volatility-double-v1",
        "Volatility ×2",
        {"calculation_type": "RISK_PARAMETER_STRESS", "volatility_multiplier": "2"},
    ),
]


def scenario(risk: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    valuation = risk["current_valuation"]
    kind = config["calculation_type"]
    result: dict[str, Any] = {
        "rule_version": SCENARIO_VERSION,
        "calculation_type": kind,
        "status": "INSUFFICIENT_DATA",
        "hypothetical": True,
        "impact_base": None,
        "impact_fraction": None,
        "stressed_value_base": None,
        "position_impacts": [],
        "unmodeled_positions": [],
        "assumptions": config,
        "warning": "Explicit hypothesis, not a forecast or maximum loss.",
    }
    if kind == "RISK_PARAMETER_STRESS":
        vol = risk.get("metrics", {}).get("annualized_volatility")
        result["stressed_annualized_volatility"] = (
            str(D(vol) * D(str(config.get("volatility_multiplier", "2"))))
            if vol is not None
            else None
        )
        result["status"] = "AVAILABLE" if vol is not None else "INSUFFICIENT_DATA"
        result["reason"] = "PARAMETER_ONLY_NO_ASSUMED_PRICE_LOSS"
        return result
    total = valuation.get("total_value_base")
    if valuation["status"] != "COMPLETE" or total is None or D(str(total)) <= 0:
        result["reason"] = "COMPLETE_POSITIVE_NAV_REQUIRED"
        return result
    shock = config.get("shock")
    if shock is None:
        result["reason"] = "EXPLICIT_SHOCK_REQUIRED"
        return result
    shock = D(str(shock))
    impact = D(0)
    if kind == "CURRENCY_TRANSLATION_SHOCK":
        currency = config.get("currency")
        if (
            not currency
            or currency == valuation["base_currency"]
            or config.get("quote_currency", valuation["base_currency"])
            != valuation["base_currency"]
        ):
            result["reason"] = "SHOCK_REQUIRES_MATCHING_FOREIGN_BASE_PAIR"
            return result
        # Net currency includes debt/cash as well as securities. Apply exactly once.
        for item in valuation["holdings"] + valuation["cash"]:
            if item["currency"] == currency:
                value = item.get("market_value_base", item.get("base_amount"))
                part = D(str(value)) * shock
                impact += part
                result["position_impacts"].append(
                    {
                        "instrument_id": item.get("instrument_id"),
                        "account_id": item["account_id"],
                        "currency": currency,
                        "impact_base": str(part),
                    }
                )
    else:
        benchmark = risk.get("benchmark")
        if kind == "BETA_BASED_MARKET_SHOCK" and (
            not config.get("benchmark_mapping_confirmed")
            or not benchmark
            or str(config.get("benchmark_id")) != benchmark["benchmark_id"]
        ):
            result["reason"] = "EXPLICIT_MATCHING_BENCHMARK_MAPPING_REQUIRED"
            return result
        selected = set(map(str, config.get("instrument_ids", [])))
        if kind == "DIRECT_POSITION_SHOCK" and selected - {
            str(h["instrument_id"]) for h in valuation["holdings"]
        }:
            result["reason"] = "SELECTED_POSITION_NOT_HELD"
            return result
        if kind == "DIRECT_POSITION_SHOCK" and not selected and not config.get("sector"):
            result["reason"] = "EXPLICIT_POSITION_SELECTION_REQUIRED"
            return result
        for holding in valuation["holdings"]:
            iid = str(holding["instrument_id"])
            beta = None
            if kind == "DIRECT_POSITION_SHOCK":
                if config.get("sector"):
                    if not holding.get("sector"):
                        result["unmodeled_positions"].append(iid)
                        continue
                    if holding["sector"].casefold() != config["sector"].casefold():
                        continue
                elif iid not in selected:
                    continue
                beta = D(1)
            else:
                info = risk.get("position_beta", {}).get(iid, {})
                if info.get("beta_status") == "AVAILABLE" and info.get("status") == "AVAILABLE":
                    beta = D(info["beta"])
            if beta is None:
                result["unmodeled_positions"].append(iid)
                continue
            price_change = beta * shock
            if price_change < -1:
                result["unmodeled_positions"].append(iid)
                continue
            part = D(str(holding["market_value_base"])) * price_change
            impact += part
            result["position_impacts"].append(
                {
                    "instrument_id": iid,
                    "impact_base": str(part),
                    "beta": str(beta) if kind == "BETA_BASED_MARKET_SHOCK" else None,
                }
            )
    partial = bool(result["unmodeled_positions"])
    result.update(
        {
            "status": "PARTIAL" if partial else "AVAILABLE",
            "modeled_impact_base": str(impact),
            "impact_base": None if partial else str(impact),
            "impact_fraction": None if partial else str(impact / D(str(total))),
            "stressed_value_base": None if partial else str(D(str(total)) + impact),
        }
    )
    return result
