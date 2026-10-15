from decimal import Decimal

import pytest

from app.recommendations.engine import evaluate, ranking_key
from app.recommendations.portfolio_context import constraints
from app.recommendations.scoring import score
from app.schemas.recommendations import InvestmentPreferences


def components():
    return {
        "expected_excess_return": 80,
        "forecast_confidence": 80,
        "quality": 80,
        "valuation": 80,
        "momentum": None,
        "risk_penalty": 10,
        "concentration_penalty": 10,
        "correlation_penalty": 10,
        "transaction_cost_penalty": 10,
    }


def test_ranking_is_stable_and_missing_scores_never_become_zero():
    rows = [(None, "missing"), ("-5", "negative"), ("50", "b"), ("50", "a")]
    assert sorted(rows, key=lambda r: ranking_key(*r)) == [
        ("50", "a"),
        ("50", "b"),
        ("-5", "negative"),
        (None, "missing"),
    ]


@pytest.mark.parametrize(
    "gate",
    [
        "NO_VALIDATED_PRODUCTION_FORECAST",
        "VALID_LATEST_PRICE",
        "VALID_FX",
        "CORPORATE_ACTION_COVERAGE",
        "VALUATION_QUALITY",
        "LIQUIDITY",
        "VALIDATED_STRATEGY",
        "RISK_CONTEXT_MATCHES_LEDGER",
        "PROFILE_CONFIRMED",
    ],
)
def test_hard_gate_cannot_be_rescued_by_scores(gate):
    result = evaluate({gate: False}, [], components(), True, {}, None)
    assert result["category"] == "INSUFFICIENT_DATA"
    assert result["scoring"]["score"] is None
    assert result["explanation"]["positive_factors"] == []
    assert gate in result["eligibility"]["missing_inputs"]


def test_delisted_and_excluded_have_no_action_character():
    result = evaluate(
        {"NO_VALIDATED_PRODUCTION_FORECAST": False},
        ["INSTRUMENT_NOT_TRADABLE"],
        components(),
        True,
        {},
        None,
    )
    assert result["category"] == "INELIGIBLE"
    assert not result["eligibility"]["permitted"]


def test_synthetic_pure_rule_exact_formula_and_optional_policy():
    result = evaluate({"SYNTHETIC_TEST_ONLY": True}, [], components(), False, {}, None)
    assert result["category"] == "CONSIDER_INCREASE"
    assert Decimal(result["scoring"]["score"]) == Decimal("58.00")
    assert result["scoring"]["components"]["momentum"]["status"] == "OPTIONAL_UNAVAILABLE"
    assert result == evaluate({"SYNTHETIC_TEST_ONLY": True}, [], components(), False, {}, None)
    data = components()
    data["valuation"] = None
    assert score(data)["score"] is None
    assert score(data)["missing_inputs"] == ["valuation"]


def test_cost_penalty_changes_score_without_imputing_missing_facts():
    data = components()
    low = Decimal(score(data)["score"])
    data["transaction_cost_penalty"] = 50
    assert Decimal(score(data)["score"]) == low - Decimal("1.2")


def test_concentration_and_unknown_metadata_constraints():
    prefs = InvestmentPreferences().model_dump(mode="json")
    value = {
        "status": "COMPLETE",
        "total_value_base": "10000",
        "cash_value_base": "1000",
        "base_currency": "CHF",
    }
    exposure = {
        "groups": {"sector": {"Tech": {"weight": ".35"}}, "country": {"US": {"weight": ".4"}}},
        "positions": {"a": {"weight": ".35"}},
        "currency": {"USD": {"net_weight": ".35"}},
    }
    known, violations = constraints(
        value, exposure, {"annualized_volatility": ".15"}, prefs, Decimal(100)
    )
    assert known and "MAX_SECTOR_WEIGHT_BREACHED" in violations
    assert "MAX_SINGLE_POSITION_WEIGHT_BREACHED" in violations
    exposure["groups"]["country"] = {"UNKNOWN": {"weight": ".4"}}
    assert not constraints(value, exposure, {"annualized_volatility": ".15"}, prefs, Decimal(100))[
        0
    ]
