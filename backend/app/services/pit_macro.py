import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import MacroObservation, RawIngestion
from app.schemas.pit import StrictModel
from app.services.fundamentals import digest
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class MacroInput(StrictModel):
    series: Literal[
        "Fed_rate",
        "SNB_rate",
        "ECB_rate",
        "yield_2Y",
        "yield_10Y",
        "yield_curve",
        "inflation",
        "VIX",
        "credit_spreads",
        "USD_CHF",
        "EUR_CHF",
        "oil",
    ]
    observation_date: date
    value: Decimal = Field(allow_inf_nan=False, max_digits=38, decimal_places=12)
    unit: Literal["PERCENT", "INDEX", "USD_PER_BARREL", "RATE"]
    known_at: AwareDatetime | None = None


class MacroImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preview(self, raw_id: UUID, user_id: UUID) -> dict[str, Any]:
        raw = await self.db.get(RawIngestion, raw_id)
        if (
            raw is None
            or raw.resource_type != "macro_import"
            or raw.request_metadata.get("user_id") != str(user_id)
        ):
            raise AppError(404, "RAW_NOT_FOUND", "Owned macro raw required")
        data = await RawIngestionService(self.db).get_verified(raw.id)
        rows: list[dict[str, Any]] = []
        errors = []
        keys = set()
        try:
            for row in csv.DictReader(StringIO(data.decode("utf-8-sig"))):
                if len(rows) >= 1000:
                    raise ValueError("Maximum 1000 macro rows")
                item = MacroInput.model_validate({k: v for k, v in row.items() if v})
                expected = (
                    "RATE"
                    if item.series in {"USD_CHF", "EUR_CHF"}
                    else "USD_PER_BARREL"
                    if item.series == "oil"
                    else "INDEX"
                    if item.series == "VIX"
                    else "PERCENT"
                )
                if item.unit != expected:
                    raise ValueError("Incompatible macro unit")
                if item.observation_date > raw.received_at.date() or (
                    item.known_at and item.known_at > raw.received_at
                ):
                    raise ValueError("Future observation")
                key = (item.series, item.observation_date)
                if key in keys:
                    raise ValueError("Ambiguous duplicate vintage")
                keys.add(key)
                rows.append(item.model_dump(mode="json"))
        except (ValueError, UnicodeError, ValidationError) as error:
            errors.append(str(error))
        return {
            "raw_id": str(raw.id),
            "rows": rows,
            "errors": errors,
            "availability": "UNVERIFIED UNTIL EXPLICIT REVIEW",
        }

    async def commit(self, raw_id: UUID, user_id: UUID) -> dict[str, int]:
        source = await SourceService(self.db).get("MANUAL_PIT", lock=True)
        SourceGate.require_enabled(source, "macro")
        preview = await self.preview(raw_id, user_id)
        if preview["errors"] or not preview["rows"]:
            raise AppError(422, "MACRO_INVALID", "Invalid macro preview")
        raw = await self.db.get(RawIngestion, raw_id)
        assert raw
        if raw.source_id != source.id:
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source mismatch")
        count = 0
        for value in preview["rows"]:
            item = MacroInput.model_validate(value)
            key = digest((item.series, item.observation_date))
            if (
                await self.db.scalars(
                    select(MacroObservation).where(
                        MacroObservation.raw_ingestion_id == raw.id, MacroObservation.row_key == key
                    )
                )
            ).first():
                continue
            previous = (
                await self.db.scalars(
                    select(MacroObservation)
                    .where(
                        MacroObservation.series == item.series,
                        MacroObservation.observation_date == item.observation_date,
                    )
                    .order_by(MacroObservation.observed_at.desc())
                    .limit(1)
                )
            ).first()
            self.db.add(
                MacroObservation(
                    series=item.series,
                    observation_date=item.observation_date,
                    value=str(item.value),
                    unit=item.unit,
                    known_at=item.known_at or raw.received_at,
                    observed_at=raw.received_at,
                    source_id=source.id,
                    raw_ingestion_id=raw.id,
                    row_key=key,
                    replaces_id=previous.id if previous else None,
                )
            )
            count += 1
        await self.db.commit()
        return {"inserted": count}
