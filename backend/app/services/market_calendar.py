from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from importlib.metadata import version
from typing import Any, cast

import exchange_calendars as xcals

from app.core.errors import AppError


@lru_cache(maxsize=2)
def calendar_for(name: str) -> Any:
    return xcals.get_calendar(name, start="1990-01-01", end="2035-12-31")


class MarketCalendarService:
    version = f"exchange-calendars-{version('exchange-calendars')}:sessions-v1"
    aliases = {
        "NYSE": "XNYS",
        "NASDAQ": "XNYS",
        "XNYS": "XNYS",
        "XNAS": "XNYS",
        "SIX": "XSWX",
        "XSWX": "XSWX",
    }

    def calendar(self, exchange: str) -> Any:
        name = self.aliases.get(exchange.upper())
        if name is None:
            raise AppError(422, "CALENDAR_UNAVAILABLE", "Explicit supported exchange required")
        return calendar_for(name)

    def is_session(self, exchange: str, day: date) -> bool:
        return bool(self.calendar(exchange).is_session(day.isoformat()))

    def sessions_between(self, exchange: str, start: date, end: date) -> list[date]:
        return [
            item.date()
            for item in self.calendar(exchange).sessions_in_range(
                start.isoformat(), end.isoformat()
            )
        ]

    def next_session(self, exchange: str, day: date) -> date:
        return cast(
            date,
            (
                self.calendar(exchange)
                .date_to_session((day + timedelta(days=1)).isoformat(), direction="next")
                .date()
            ),
        )

    def previous_session(self, exchange: str, day: date) -> date:
        return cast(
            date,
            (
                self.calendar(exchange)
                .date_to_session((day - timedelta(days=1)).isoformat(), direction="previous")
                .date()
            ),
        )

    def session_open(self, exchange: str, day: date) -> datetime:
        return cast(
            datetime,
            self.calendar(exchange).session_open(day.isoformat()).to_pydatetime().astimezone(UTC),
        )

    def session_close(self, exchange: str, day: date) -> datetime:
        return cast(
            datetime,
            (
                self.calendar(exchange)
                .session_close(day.isoformat())
                .to_pydatetime()
                .astimezone(UTC)
            ),
        )

    def horizon(self, exchange: str, day: date, count: int) -> date:
        if count < 1 or count > 500:
            raise AppError(422, "HORIZON_INVALID", "Session horizon must be 1..500")
        current = day
        for _ in range(count):
            current = self.next_session(exchange, current)
        return current
