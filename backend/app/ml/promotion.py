"""Acceptance criteria are fixed before final test evaluation."""

from typing import Any

PROMOTION_RULES = {
    "version": "p7-conservative-promotion-v1",
    "minimum_training_observations": 1000,
    "minimum_oos_observations": 500,
    "minimum_oos_signal_dates": 600,
    "minimum_folds": 3,
    "maximum_ece": 0.05,
    "minimum_relative_baseline_improvement": 0.02,
    "minimum_interval_coverage": 0.75,
    "maximum_interval_coverage": 0.95,
    "maximum_fold_loss_ratio": 2.0,
}


def promotion_reasons(evidence: dict[str, Any]) -> list[str]:
    reasons = []
    checks = {
        "REAL_STRICT_PIT_EVIDENCE_REQUIRED": evidence.get("production_data_eligible") is True,
        "SYNTHETIC_EVIDENCE_FORBIDDEN": evidence.get("synthetic_evidence") is False,
        "TRAINING_HISTORY_INSUFFICIENT": evidence.get("training_observations", 0) >= 1000,
        "OOS_HISTORY_INSUFFICIENT": evidence.get("oos_observations", 0) >= 500
        and evidence.get("oos_signal_dates", 0) >= 600,
        "WALK_FORWARD_INSUFFICIENT": evidence.get("folds", 0) >= 3,
        "LEAKAGE_AUDIT_REQUIRED": evidence.get("leakage_verified") is True,
        "BASELINE_COMPARISON_FAILED": evidence.get("baseline_passed") is True,
        "CALIBRATION_FAILED": evidence.get("calibration_passed") is True,
        "INTERVAL_COVERAGE_FAILED": evidence.get("interval_passed") is True,
        "PERIOD_INSTABILITY": evidence.get("stability_passed") is True,
        "COST_BACKTEST_REQUIRED": evidence.get("financial_backtest_passed") is True,
        "MODEL_CARD_REQUIRED": evidence.get("model_card_verified") is True,
        "ARTIFACT_VERIFICATION_REQUIRED": evidence.get("artifact_verified") is True,
        "UNVERIFIED_CODE": evidence.get("code_verified") is True,
    }
    for code, passed in checks.items():
        if not passed:
            reasons.append(code)
    return reasons
