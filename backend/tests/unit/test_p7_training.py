from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.ml.readiness import audit_readiness
from app.ml.training import TrainingInput, train_kernel
from app.ml.validation import FoldWindow, split_rows
from app.services.market_calendar import MarketCalendarService


def synthetic_rows():
    calendar = MarketCalendarService()
    rows = []
    for index, day in enumerate(
        calendar.sessions_between("NYSE", date(2015, 1, 2), date(2024, 12, 31))
    ):
        cutoff = calendar.session_close("NYSE", day) + timedelta(minutes=30)
        end_day = calendar.horizon("NYSE", day, 30)
        end = calendar.session_close("NYSE", end_day)
        value = ((index % 19) - 9) / 10
        rows.append(
            {
                "instrument_id": "synthetic",
                "date": day.isoformat(),
                "eligible": True,
                "exclusions": [],
                "information_cutoff_at": cutoff.isoformat(),
                "features": {"test_feature": {"value": str(value), "missing_flag": False}},
                "target": {
                    "status": "AVAILABLE",
                    "signal_as_of": cutoff.isoformat(),
                    "horizon_sessions": 30,
                    "label_start": calendar.session_open(
                        "NYSE", calendar.next_session("NYSE", day)
                    ).isoformat(),
                    "label_end": end.isoformat(),
                    "label_available_at": (end + timedelta(minutes=1)).isoformat(),
                    "classification": int(value > 0),
                    "excess_return": str(value * 0.01),
                    "instrument_return": str(value * 0.02),
                },
            }
        )
    return rows


def window():
    return FoldWindow(
        validation_start="2020-01-02T00:00:00Z",
        calibration_start="2021-01-04T00:00:00Z",
        test_start="2023-01-03T00:00:00Z",
        final_end="2025-06-02T00:00:00Z",
        embargo_sessions=30,
    )


def test_whole_training_pipeline_reproducible_and_synthetic_not_promotable():
    rows = synthetic_rows()
    readiness = audit_readiness(
        {
            "availability_mode": "STRICT_PIT",
            "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE",
        },
        rows,
        {"survivorship_risk": False},
        ["test_feature"],
        30,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    config = TrainingInput(
        dataset_id=uuid4(),
        model_type="LOGISTIC",
        target="classification",
        feature_names=["test_feature"],
        required_features=["test_feature"],
        folds=[window()],
    )
    first = train_kernel(config, rows, readiness, {"synthetic": "NYSE"})
    second = train_kernel(config, rows, readiness, {"synthetic": "NYSE"})
    assert first == second
    assert first["folds"][0]["calibration"]["status"] == "AVAILABLE"
    assert first["folds"][0]["test_metrics"]["roc_auc"] > 0.99
    assert not readiness["production_data_eligible"]
    partitions = first["folds"][0]["partitions"]
    assert not set(partitions["calibration"]) & set(partitions["test"])


def test_future_information_and_insufficient_embargo_rejected():
    rows = synthetic_rows()[:1]
    rows[0]["information_cutoff_at"] = "2027-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="LEAKAGE"):
        split_rows(rows, window(), 30, {"synthetic": "NYSE"}, ["0"])
    with pytest.raises(ValueError, match="INSUFFICIENT_EMBARGO"):
        split_rows([], window(), 90, {}, [])
