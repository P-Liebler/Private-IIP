from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.services.sources import SourceGate, SourceService


class SnbFxCollector:
    """Fail closed until the daily series and response schema are documented."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def collect(self, start: date, end: date) -> None:
        source = await SourceService(self.db).get("SNB")
        SourceGate.require_enabled(source, "fx_rates")
        raise AppError(
            503,
            "SOURCE_FORMAT_UNVERIFIED",
            "SNB daily FX series and response format require verification before collection",
        )
