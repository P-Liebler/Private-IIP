from uuid import UUID

RULE_ID = UUID("2c8ca1b7-4587-5f12-b801-899ea09f1e9f")
RULE_NAME = "recommendation-score-v1"
WEIGHTS = {
    "expected_excess_return": ".25",
    "forecast_confidence": ".15",
    "quality": ".20",
    "valuation": ".15",
    "momentum": ".05",
    "risk_penalty": "-.08",
    "concentration_penalty": "-.05",
    "correlation_penalty": "-.04",
    "transaction_cost_penalty": "-.03",
}
RULE_CONFIG = {
    "name": RULE_NAME,
    "weights": WEIGHTS,
    "optional_components": ["momentum"],
    "missing_policy": "OPTIONAL_OMITTED_WITHOUT_RENORMALIZATION; REQUIRED_ABSTAIN",
    "normalization": "clip to [0,100]; excess return: 50+500*r; costs: 10000*cost/amount",
    "category_thresholds": {"CONSIDER_INCREASE": "55", "HOLD": "35", "WATCH": "20"},
    "forecast_max_age_hours": 24,
    "risk_max_age_hours": 24,
    "minimum_risk_observations": 252,
    "maximum_interval_width": ".50",
    "minimum_empirical_coverage": ".85",
    "baseline_policy": ["NO_CHANGE", "BENCHMARK_ONLY", "EQUAL_WEIGHT", "MOMENTUM", "QUALITY_VALUE"],
    "production_evidence": "REAL_STRICT_PIT_OUT_OF_SAMPLE_WITH_COSTS_AND_OPERATOR_REVIEW",
    "optimal_weights_proven": False,
}
