from decimal import Decimal
from typing import Any

D = Decimal


def exposures(
    holdings: list[dict[str, Any]], cash: list[dict[str, Any]], total: Decimal | None
) -> dict[str, Any]:
    if (
        total is None
        or total <= 0
        or any(h.get("market_value_base") is None for h in holdings)
        or any(c.get("base_amount") is None for c in cash)
    ):
        return {"status": "INSUFFICIENT_DATA", "concentration": None, "groups": {}, "currency": {}}
    positions: dict[str, Decimal] = {}
    groups: dict[str, dict[str, Decimal]] = {
        key: {} for key in ("sector", "industry", "country", "trading_currency")
    }
    currency: dict[str, Decimal] = {}
    for holding in holdings:
        value = D(str(holding["market_value_base"]))
        iid = str(holding["instrument_id"])
        positions[iid] = positions.get(iid, D(0)) + value
        for key in groups:
            label = holding.get("currency") if key == "trading_currency" else holding.get(key)
            label = label or "UNKNOWN"
            groups[key][label] = groups[key].get(label, D(0)) + value
        currency[holding["currency"]] = currency.get(holding["currency"], D(0)) + value
    for account in cash:
        currency[account["currency"]] = currency.get(account["currency"], D(0)) + D(
            str(account["base_amount"])
        )
    weights = sorted((v / total for v in positions.values()), reverse=True)
    return {
        "status": "AVAILABLE",
        "total_value_base": str(total),
        "concentration": {
            "largest_position_weight": str(weights[0]) if weights else "0",
            "top_3_weight": str(sum(weights[:3], D(0))),
            "top_5_weight": str(sum(weights[:5], D(0))),
            "hhi": str(sum((w * w for w in weights), D(0))),
            "denominator": "COMPLETE_PORTFOLIO_NAV",
            "cash_in_hhi": False,
        },
        "positions": {
            k: {"value_base": str(v), "weight": str(v / total)} for k, v in positions.items()
        },
        "groups": {
            key: {k: {"value_base": str(v), "weight": str(v / total)} for k, v in entries.items()}
            for key, entries in groups.items()
        },
        "currency": {
            k: {"net_value_base": str(v), "net_weight": str(v / total)} for k, v in currency.items()
        },
        "economic_currency_exposure": {
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_VERIFIED_REVENUE_CURRENCY_BREAKDOWN",
        },
    }


def liquidity_score(holdings: list[dict[str, Any]], evidence: dict[str, Any]) -> dict[str, Any]:
    total = sum(
        (
            D(str(h["market_value_base"]))
            for h in holdings
            if h.get("market_value_base") is not None
        ),
        D(0),
    )
    inputs, weighted, missing = [], D(0), []
    for holding in holdings:
        iid = str(holding["instrument_id"])
        data = evidence.get(iid, {})
        volume = data.get("average_volume")
        if volume is None or D(str(volume)) <= 0 or data.get("observations", 0) < 20:
            missing.append(iid)
            continue
        participation = D(str(holding["quantity"])) / D(str(volume))
        weight = D(str(holding["market_value_base"])) / total if total > 0 else None
        if weight is not None:
            weighted += max(D(0), 1 - participation / D(".1")) * 100 * weight
        inputs.append(
            {
                "instrument_id": iid,
                "participation": str(participation),
                "weight": str(weight),
                "evidence": data,
            }
        )
    return {
        "score": str(weighted) if holdings and total > 0 and not missing else None,
        "inputs": inputs,
        "missing_inputs": missing or ([] if holdings else ["securities_positions"]),
        "formula": "securities_weighted_clip("
        "100*(1-position_quantity/average_20_session_volume/.1))",
        "quality": "VOLUME_ONLY_PROXY_NO_SPREAD_OR_EXECUTION_GUARANTEE",
    }


def health(
    exposure: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any] | None = None,
    base_currency: str | None = None,
    liquidity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def score(
        name: str, value: Decimal | None, inputs: dict[str, Any], missing: list[str]
    ) -> dict[str, Any]:
        return {
            "name": name,
            "score": str(max(D(0), min(D(100), value))) if value is not None else None,
            "status": "AVAILABLE" if value is not None else "INSUFFICIENT_DATA",
            "inputs": inputs,
            "weights": {"single_rule": "1"},
            "quality": "HARD_GATES_FIRST",
            "rule_version": "risk-health-v1",
            "missing_inputs": missing,
        }

    concentration = exposure.get("concentration")
    hhi = D(concentration["hhi"]) if concentration else None
    largest = D(concentration["largest_position_weight"]) if concentration else None
    volatility = (
        D(metrics["annualized_volatility"])
        if metrics.get("annualized_volatility") is not None
        else None
    )
    quality_value = (
        D(str(quality["score"])) if quality and quality.get("score") is not None else None
    )
    foreign = (
        sum(
            (
                abs(D(v["net_weight"]))
                for k, v in exposure.get("currency", {}).items()
                if k != base_currency
            ),
            D(0),
        )
        if base_currency and exposure.get("status") == "AVAILABLE"
        else None
    )
    return {
        "status": "AVAILABLE"
        if all(
            v is not None
            for v in (
                hhi,
                largest,
                volatility,
                quality_value,
                foreign,
                liquidity.get("score") if liquidity else None,
            )
        )
        else "INSUFFICIENT_DATA",
        "overall_score": None,
        "subscores": [
            score(
                "Diversification",
                (1 - hhi) * 100 if hhi is not None else None,
                {"hhi": str(hhi) if hhi is not None else None, "formula": "100*(1-HHI)"},
                [] if hhi is not None else ["complete_exposure"],
            ),
            score(
                "Concentration",
                (1 - largest) * 100 if largest is not None else None,
                {
                    "largest_weight": str(largest) if largest is not None else None,
                    "formula": "100*(1-largest_weight)",
                },
                [] if largest is not None else ["complete_exposure"],
            ),
            score(
                "Volatility",
                (1 - volatility / D(".5")) * 100 if volatility is not None else None,
                {
                    "annualized_volatility": str(volatility) if volatility is not None else None,
                    "formula": "100*(1-vol/.5), clipped 0..100",
                },
                [] if volatility is not None else ["validated_returns"],
            ),
            score(
                "Quality",
                quality_value,
                quality or {},
                [] if quality_value is not None else ["complete_versioned_quality_scores"],
            ),
            score(
                "Currency Risk",
                (1 - foreign) * 100 if foreign is not None else None,
                {
                    "trading_currency_exposure": exposure.get("currency", {}),
                    "formula": "100*(1-sum(abs(foreign_net_weights)))",
                    "scope": "ACCOUNTING_TRANSLATION_CONCENTRATION_NOT_ECONOMIC_FX_VOLATILITY",
                },
                [] if foreign is not None else ["complete_current_fx_exposure"],
            ),
            score(
                "Liquidity",
                D(str(liquidity["score"]))
                if liquidity and liquidity.get("score") is not None
                else None,
                liquidity or {},
                liquidity.get("missing_inputs", [])
                if liquidity
                else ["verified_volume_and_position_size"],
            ),
        ],
        "policy": "NO_REWEIGHTING_AROUND_MISSING_RISK_DATA",
    }
