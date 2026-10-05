from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import InstrumentIdentifier
from app.schemas.imports import CsvPreviewResponse, CsvPreviewRow
from app.services.instruments import normalize_identifier
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

_ALIASES = {
    "date": "date",
    "trading_date": "date",
    "datum": "date",
    "close": "close",
    "adjusted_close": "adjusted_close",
    "adj_close": "adjusted_close",
    "closing_price": "close",
    "schlusskurs": "close",
    "ticker": "ticker",
    "symbol": "ticker",
    "isin": "isin",
    "figi": "figi",
    "open": "open",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "currency": "currency",
    "waehrung": "currency",
}


class CsvPreviewService:
    def __init__(self, db: AsyncSession, raw: RawIngestionService | None = None) -> None:
        self.db = db
        self.raw = raw or RawIngestionService(db)

    async def preview(self, data: bytes, *, filename: str) -> CsvPreviewResponse:
        source = await SourceService(self.db).get("MANUAL_CSV")
        SourceGate.require_enabled(source, "manual_upload")
        if not data or len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV must be between 1 byte and 5 MB")
        raw = await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="manual_csv_preview",
            content_type="text/csv",
            request_metadata={"filename": filename},
        )
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return CsvPreviewResponse(
                raw_ingestion_id=raw.id,
                detected_columns=[],
                possible_mapping={},
                sample_rows=[],
                validation_errors=["CSV must be UTF-8 encoded"],
                row_count=0,
            )
        reader = csv.DictReader(StringIO(text, newline=""))
        columns = reader.fieldnames or []
        mapping: dict[str, str] = {}
        errors: list[str] = []
        for column in columns:
            canonical = _ALIASES.get(column.strip().lower())
            if canonical is None:
                errors.append(f"Unknown column: {column}")
            elif canonical in mapping.values():
                errors.append(f"Duplicate mapping for {canonical}")
            else:
                mapping[column] = canonical
        present = set(mapping.values())
        for required in ("date", "close"):
            if required not in present:
                errors.append(f"Missing required column: {required}")
        if not {"ticker", "isin", "figi"} & present:
            errors.append("Missing instrument identifier column")
        rows: list[CsvPreviewRow] = []
        row_count = 0
        try:
            for line, row in enumerate(reader, start=2):
                row_count += 1
                if row_count > 10_000:
                    errors.append("CSV preview is limited to 10000 rows")
                    break
                if line > 51:
                    continue
                normalized: dict[str, str | None] = {
                    canonical: row.get(original) for original, canonical in mapping.items()
                }
                row_errors: list[str] = []
                as_of: date | None = None
                try:
                    as_of = date.fromisoformat(normalized.get("date") or "")
                except ValueError:
                    row_errors.append("Invalid or missing ISO date")
                try:
                    close = Decimal(normalized.get("close") or "")
                    if not close.is_finite() or close <= 0:
                        raise InvalidOperation
                    normalized["close"] = str(close)
                except (InvalidOperation, ValueError):
                    row_errors.append("Invalid or missing positive close")
                if None in row:
                    row_errors.append("Malformed row with extra fields")
                instrument_id, status = await self._resolve(normalized, as_of, row_errors)
                rows.append(
                    CsvPreviewRow(
                        line=line,
                        values=normalized,
                        resolution_status=status,
                        instrument_id=instrument_id,
                        errors=row_errors,
                    )
                )
        except csv.Error:
            errors.append("Malformed CSV structure")
        if row_count == 0:
            errors.append("CSV contains no data rows")
        return CsvPreviewResponse(
            raw_ingestion_id=raw.id,
            detected_columns=columns,
            possible_mapping=mapping,
            sample_rows=rows,
            validation_errors=errors,
            row_count=row_count,
        )

    async def _resolve(
        self, row: dict[str, str | None], as_of: date | None, errors: list[str]
    ) -> tuple[UUID | None, str]:
        if as_of is None:
            return None, "UNRESOLVED"
        found: list[set[UUID]] = []
        for kind in ("ISIN", "FIGI", "TICKER"):
            value = row.get(kind.lower())
            if not value:
                continue
            try:
                normalized = normalize_identifier(kind, value)
            except ValueError:
                errors.append(f"Invalid {kind} value")
                return None, "UNRESOLVED"
            row[kind.lower()] = normalized
            ids = set(
                (
                    await self.db.scalars(
                        select(InstrumentIdentifier.instrument_id).where(
                            InstrumentIdentifier.type == kind,
                            InstrumentIdentifier.value == normalized,
                            InstrumentIdentifier.valid_from <= as_of,
                            or_(
                                InstrumentIdentifier.valid_to.is_(None),
                                InstrumentIdentifier.valid_to > as_of,
                            ),
                        )
                    )
                ).all()
            )
            found.append(ids)
        if not found:
            errors.append("Row has no instrument identifier")
            return None, "UNRESOLVED"
        if any(not ids for ids in found):
            return None, "AMBIGUOUS" if any(ids for ids in found) else "UNRESOLVED"
        common = set.intersection(*found)
        if len(common) == 1 and all(ids == common for ids in found):
            return next(iter(common)), "RESOLVED"
        return None, "AMBIGUOUS"
