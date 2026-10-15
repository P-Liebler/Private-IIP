from decimal import Decimal
from typing import Any

from app.recommendations.contracts import RULE_NAME
from app.recommendations.eligibility import RecommendationEligibilityService
from app.recommendations.scoring import score


def ranking_key(value: str | None, instrument_id: str) -> tuple[bool, Decimal, str]:
    """Eligible numeric scores first; unavailable scores have no numeric rank value."""
    return (value is None, -Decimal(value) if value is not None else Decimal(0), instrument_id)


def evaluate(
    checks: dict[str, bool],
    violations: list[str],
    components: dict[str, Any],
    held: bool,
    references: dict[str, Any],
    impact: dict[str, Any] | None,
) -> dict[str, Any]:
    eligibility = RecommendationEligibilityService.evaluate(checks, violations)
    scoring = (
        score(components)
        if eligibility["permitted"]
        else {"score": None, "components": {}, "missing_inputs": eligibility["missing_inputs"]}
    )
    if scoring["score"] is None and eligibility["permitted"]:
        eligibility = RecommendationEligibilityService.evaluate(
            {**checks, **{f"SCORING_{k.upper()}": False for k in scoring["missing_inputs"]}}, []
        )
    if not eligibility["permitted"]:
        category = eligibility["status"]
    else:
        value = Decimal(scoring["score"])
        category = (
            "CONSIDER_INCREASE"
            if value >= 55
            else "HOLD"
            if held and value >= 35
            else "WATCH"
            if value >= 20
            else "REVIEW_REDUCE"
            if held
            else "AVOID_NEW_EXPOSURE"
        )
    available = scoring["components"]
    return {
        "category": category,
        "eligibility": eligibility,
        "scoring": scoring,
        "explanation": {
            "recommendation_category": category,
            "eligibility_status": eligibility["status"],
            "positive_factors": sorted(
                k for k, v in available.items() if Decimal(v.get("contribution", "0")) > 0
            ),
            "negative_factors": sorted(
                k for k, v in available.items() if Decimal(v.get("contribution", "0")) < 0
            ),
            "portfolio_impact": impact,
            "risk_impact": impact.get("metrics") if impact else None,
            "cost_estimate": impact.get("costs_base") if impact else None,
            "missing_inputs": eligibility["missing_inputs"],
            "warnings": eligibility["violations"],
            "rules_version": RULE_NAME,
            "model_version": references.get("model_versions", []),
            "source_references": references,
            "notice": "NO_VALIDATED_INVESTMENT_RECOMMENDATIONS"
            if not eligibility["permitted"]
            else None,
        },
    }
