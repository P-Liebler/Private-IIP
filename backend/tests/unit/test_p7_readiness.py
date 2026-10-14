from copy import deepcopy
from datetime import UTC, datetime

from app.ml.readiness import audit_readiness

NOW = datetime(2026, 10, 14, tzinfo=UTC)
CONFIG = {"availability_mode": "STRICT_PIT", "data_context": "USER_ARCHIVE"}
QUALITY = {"survivorship_risk": False}


def observation():
    return {
        "instrument_id": "instrument",
        "date": "2024-01-02",
        "eligible": True,
        "exclusions": [],
        "information_cutoff_at": "2024-01-02T21:30:00+00:00",
        "features": {"momentum_20": {"value": "0.1", "missing_flag": False}},
        "target": {
            "status": "AVAILABLE",
            "classification": 1,
            "excess_return": "0.1",
            "instrument_return": "0.2",
            "horizon_sessions": 30,
            "signal_as_of": "2024-01-02T21:30:00+00:00",
            "label_start": "2024-01-03T14:30:00+00:00",
            "label_end": "2024-02-15T21:00:00+00:00",
            "label_available_at": "2024-02-15T21:01:00+00:00",
        },
    }


def audit(row, config=None):
    return audit_readiness(config or CONFIG, [row], QUALITY, ["momentum_20"], 30, NOW)


def test_small_valid_archive_is_insufficient():
    result = audit(observation())
    assert result["status"] == "INSUFFICIENT_HISTORY"
    assert result["eligible_observations"] == 1
    assert not result["production_data_eligible"]


def test_missing_financial_feature_never_imputed_by_readiness():
    row = observation()
    row["features"]["momentum_20"]["value"] = None
    result = audit(row)
    assert result["eligible_observations"] == 0
    assert result["missing_features"] == {"momentum_20": 1}


def test_future_label_rejected():
    row = observation()
    row["target"]["label_available_at"] = "2027-01-01T00:00:00+00:00"
    result = audit(row)
    assert result["status"] == "DATA_QUALITY_FAILED"
    assert result["eligible_observations"] == 0


def test_reconstruction_is_research_only():
    config = {**CONFIG, "availability_mode": "RECONSTRUCTED_HISTORICAL"}
    assert audit(observation(), config)["status"] == "RECONSTRUCTED_RESEARCH_ONLY"


def test_synthetic_can_never_establish_real_data_release():
    rows = []
    for i in range(600):
        row = deepcopy(observation())
        row["date"] = str(i)
        rows.append(row)
    result = audit_readiness(
        {**CONFIG, "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE"},
        rows,
        QUALITY,
        ["momentum_20"],
        30,
        NOW,
    )
    assert result["status"] == "STRICT_PIT_ELIGIBLE"
    assert result["synthetic_evidence"]
    assert not result["production_data_eligible"]
