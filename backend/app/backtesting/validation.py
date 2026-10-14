from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.services.market_calendar import MarketCalendarService

AvailabilityMode = Literal["STRICT_PIT", "RECONSTRUCTED_HISTORICAL"]
VERIFIED = {"VERIFIED_PUBLIC_TIMESTAMP", "VERIFIED_SOURCE_DOCUMENT", "LOCAL_FIRST_OBSERVATION"}


def available(
    mode: AvailabilityMode,
    cutoff: datetime,
    known_at: datetime,
    observed_at: datetime,
    level: str,
    reviewed_at: datetime | None = None,
) -> bool:
    if mode == "RECONSTRUCTED_HISTORICAL":
        return known_at <= cutoff  # caller supplies event availability only for market observations
    if reviewed_at is not None and reviewed_at > cutoff:
        return False
    if level not in VERIFIED or observed_at > cutoff:
        return False
    # An assertion can never backdate local availability.
    return (observed_at if level == "LOCAL_FIRST_OBSERVATION" else known_at) <= cutoff


def validate_execution(
    signal: datetime,
    cutoff: datetime,
    tradable: datetime,
    timestamp: datetime,
    price: Decimal | None,
    market_open: bool,
) -> None:
    if signal < cutoff or timestamp <= signal or timestamp < tradable or not market_open:
        raise ValueError("EXECUTION_TIME_REJECTED")
    if price is None or not price.is_finite() or price <= 0:
        raise ValueError("EXECUTION_UNAVAILABLE")


@dataclass(frozen=True)
class LabelInterval:
    id: str
    signal_as_of: datetime
    label_start: datetime
    label_end: datetime
    label_available_at: datetime


class WalkForwardSplitter:
    def split(
        self,
        rows: list[LabelInterval],
        validation_start: datetime,
        test_start: datetime,
        final_end: datetime,
        embargo_start: datetime,
        embargo_sessions: int,
        horizon: int,
        exchange: str = "NYSE",
    ) -> dict[str, list[str]]:
        if (
            embargo_sessions < horizon
            or not embargo_start < validation_start < test_start < final_end
        ):
            raise ValueError("EMBARGO_OR_SPLIT_INVALID")
        calendar = MarketCalendarService()
        day = validation_start.date()
        test_day = test_start.date()
        for _ in range(embargo_sessions):
            day = calendar.previous_session(exchange, day)
            test_day = calendar.previous_session(exchange, test_day)
        expected = calendar.session_close(exchange, day)
        test_embargo = calendar.session_close(exchange, test_day)
        if embargo_start != expected:
            raise ValueError("EMBARGO_NOT_SESSION_BASED")
        result: dict[str, list[str]] = {"training": [], "validation": [], "test": [], "purged": []}
        for r in sorted(rows, key=lambda item: item.signal_as_of):
            if not r.signal_as_of <= r.label_start < r.label_end <= r.label_available_at:
                raise ValueError("LABEL_INTERVAL_INVALID")
            if (
                r.signal_as_of < embargo_start
                and r.label_end < embargo_start
                and r.label_available_at < embargo_start
            ):
                result["training"].append(r.id)
            elif (
                validation_start <= r.signal_as_of < test_embargo
                and r.label_end < test_embargo
                and r.label_available_at < test_embargo
            ):
                result["validation"].append(r.id)
            elif test_start <= r.signal_as_of and r.label_available_at <= final_end:
                result["test"].append(r.id)
            else:
                result["purged"].append(r.id)
        return result
