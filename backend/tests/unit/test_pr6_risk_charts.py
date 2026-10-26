from copy import deepcopy
from decimal import Decimal

from app.services.risk_charts import risk_chart_series


def source():
    return {
        "quality": {"complete_return_series": True},
        "return_observations": [
            {"date": "2026-10-19", "return": None, "status": "AVAILABLE"},
            {"date": "2026-10-20", "return": "0.1", "status": "AVAILABLE"},
            {"date": "2026-10-21", "return": "-0.2", "status": "AVAILABLE"},
        ],
        "benchmark": {"instrument_id": "benchmark"},
        "asset_quality": {"benchmark": {"coverage_id": "SYNTHETIC_REVIEW", "status": "AVAILABLE"}},
        "asset_returns": {"benchmark": {"2026-10-20": "0.05", "2026-10-21": "-0.1"}},
    }


def test_compound_and_drawdown_use_archived_decimal_returns_and_never_mutate_snapshot():
    original = source()
    before = deepcopy(original)
    result = risk_chart_series(original)
    assert Decimal(result["returns"][-1]["value"]) == Decimal("-0.12")
    assert Decimal(result["drawdown"][-1]["value"]) == Decimal("-0.2")
    assert Decimal(result["benchmark"][-1]["value"]) == Decimal("-0.055")
    assert original == before
    assert risk_chart_series(original)["derived_content_hash"] == result["derived_content_hash"]


def test_gaps_suspend_charts_and_missing_benchmark_does_not_fake_zero_comparison():
    incomplete = source()
    incomplete["quality"]["complete_return_series"] = False
    assert risk_chart_series(incomplete)["returns"] == []
    incomplete = source()
    incomplete["return_observations"][1]["return"] = None
    assert risk_chart_series(incomplete)["status"] == "DATA_UNAVAILABLE"
    incomplete = source()
    incomplete["asset_returns"]["benchmark"].pop("2026-10-21")
    output = risk_chart_series(incomplete)
    assert output["status"] == "AVAILABLE" and output["benchmark"] == []
    assert output["benchmark_status"] == "UNAVAILABLE"
