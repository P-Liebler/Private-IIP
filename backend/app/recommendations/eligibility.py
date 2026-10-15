from typing import Any


class RecommendationEligibilityService:
    """Pure hard gates. Only the service constructs trusted input evidence."""

    @staticmethod
    def evaluate(checks: dict[str, bool], violations: list[str]) -> dict[str, Any]:
        missing = sorted(name for name, passed in checks.items() if not passed)
        status = "INELIGIBLE" if violations else "INSUFFICIENT_DATA" if missing else "ELIGIBLE"
        return {
            "status": status,
            "permitted": status == "ELIGIBLE",
            "checks": checks,
            "missing_inputs": missing,
            "violations": sorted(set(violations)),
        }
