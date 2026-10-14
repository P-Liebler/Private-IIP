"""Four chronological windows with exchange-session embargo and actual-label purge."""

from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.pit import StrictModel
from app.services.market_calendar import MarketCalendarService


class FoldWindow(StrictModel):
    validation_start: AwareDatetime
    calibration_start: AwareDatetime
    test_start: AwareDatetime
    final_end: AwareDatetime
    embargo_sessions: int = Field(ge=30, le=252)

    @model_validator(mode="after")
    def chronological(self) -> "FoldWindow":
        if not self.validation_start < self.calibration_start < self.test_start < self.final_end:
            raise ValueError("CHRONOLOGICAL_WINDOWS_REQUIRED")
        return self


def split_rows(
    rows: list[dict[str, Any]],
    window: FoldWindow,
    horizon: int,
    exchanges: dict[str, str],
    eligible_ids: list[str],
) -> dict[str, list[str]]:
    if window.embargo_sessions < horizon:
        raise ValueError("INSUFFICIENT_EMBARGO")
    calendar = MarketCalendarService()
    result: dict[str, list[str]] = {
        k: [] for k in ("training", "validation", "calibration", "test", "purged")
    }
    boundaries: dict[str, list[datetime]] = {}
    eligible = set(eligible_ids)
    for index, row in enumerate(rows):
        if str(index) not in eligible:
            continue
        exchange = exchanges[row["instrument_id"]]
        if exchange not in boundaries:
            bounds = []
            for boundary in (window.validation_start, window.calibration_start, window.test_start):
                day = boundary.date()
                for _ in range(window.embargo_sessions):
                    day = calendar.previous_session(exchange, day)
                bounds.append(calendar.session_close(exchange, day))
            boundaries[exchange] = bounds
        training_end, validation_end, calibration_end = boundaries[exchange]
        target = row["target"]
        signal, start, end, available = (
            datetime.fromisoformat(target[k])
            for k in ("signal_as_of", "label_start", "label_end", "label_available_at")
        )
        cutoff = datetime.fromisoformat(row["information_cutoff_at"])
        if not cutoff <= signal < start < end <= available:
            raise ValueError("LEAKAGE_LABEL_INTERVAL")
        partition = "purged"
        if signal < training_end and available < training_end:
            partition = "training"
        elif window.validation_start <= signal < validation_end and available < validation_end:
            partition = "validation"
        elif window.calibration_start <= signal < calibration_end and available < calibration_end:
            partition = "calibration"
        elif window.test_start <= signal and available <= window.final_end:
            partition = "test"
        result[partition].append(str(index))
    return result
