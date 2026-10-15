from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.schemas.risk import HypotheticalTrade

D = Decimal


def candidate_trade(
    iid: UUID, side: str, amount: Decimal, held_value: Decimal
) -> HypotheticalTrade:
    if side == "SELL":
        if held_value <= 0 or amount > held_value:
            raise AppError(
                422, "CANDIDATE_SELL_EXCEEDS_POSITION", "Hypothetical sale exceeds the held value"
            )
        return HypotheticalTrade(instrument_id=iid, side="SELL", sell_fraction=amount / held_value)
    return HypotheticalTrade(instrument_id=iid, side="BUY", amount_base=amount)


def valuation_identity(value: dict[str, Any]) -> dict[str, Any]:
    """Compare economic/version inputs, excluding wall-clock and descriptive enrichment."""
    return {
        "transactions": sorted(map(str, value["transaction_ids"])),
        "nav": str(value["total_value_base"]),
        "base_currency": value["base_currency"],
        "cash": sorted(
            (
                str(c["account_id"]),
                c["currency"],
                str(c["amount"]),
                str(c["base_amount"]),
                str(c.get("fx", {}).get("rate")),
            )
            for c in value["cash"]
        ),
        "holdings": sorted(
            (
                str(h["account_id"]),
                str(h["instrument_id"]),
                str(h["quantity"]),
                str(h["price_version_id"]),
                str(h["market_value_base"]),
                str(h.get("fx", {}).get("rate")),
            )
            for h in value["holdings"]
        ),
    }


def constraints(
    value: dict[str, Any],
    exposure: dict[str, Any],
    metrics: dict[str, Any],
    profile: dict[str, Any],
    amount: Decimal,
) -> tuple[bool, list[str]]:
    violations: list[str] = []
    nav = value.get("total_value_base")
    if value.get("status") != "COMPLETE" or nav is None or D(str(nav)) <= 0:
        return False, violations
    if value.get("base_currency") != profile["base_currency"]:
        violations.append("PROFILE_BASE_CURRENCY_MISMATCH")
    for key, limit in (("sector", "max_sector_weight"), ("country", "max_country_weight")):
        groups = exposure.get("groups", {}).get(key, {})
        if "UNKNOWN" in groups or not groups:
            return False, violations
        if any(D(v["weight"]) > D(profile[limit]) for v in groups.values()):
            violations.append(limit.upper() + "_BREACHED")
    if any(
        D(v["weight"]) > D(profile["max_single_position_weight"])
        for v in exposure.get("positions", {}).values()
    ):
        violations.append("MAX_SINGLE_POSITION_WEIGHT_BREACHED")
    if any(
        abs(D(v["net_weight"])) > D(profile["max_currency_exposure"])
        for currency, v in exposure.get("currency", {}).items()
        if currency != profile["base_currency"]
    ):
        violations.append("MAX_CURRENCY_EXPOSURE_BREACHED")
    if value.get("cash_value_base") is None:
        return False, violations
    if D(str(value["cash_value_base"])) / D(str(nav)) < D(profile["minimum_cash_reserve"]):
        violations.append("MINIMUM_CASH_RESERVE_BREACHED")
    if amount > D(profile["maximum_new_investment"]):
        violations.append("MAXIMUM_NEW_INVESTMENT_BREACHED")
    if amount / D(str(nav)) > D(profile["maximum_turnover"]):
        violations.append("MAXIMUM_TURNOVER_BREACHED")
    vol = metrics.get("annualized_volatility")
    if vol is None:
        return False, violations
    if D(str(vol)) > D(profile["maximum_portfolio_volatility"]):
        violations.append("MAXIMUM_PORTFOLIO_VOLATILITY_BREACHED")
    return True, violations
