from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CsvPreviewRow(BaseModel):
    line: int
    values: dict[str, str | None]
    resolution_status: str
    instrument_id: UUID | None
    errors: list[str]


class CsvPreviewResponse(BaseModel):
    raw_ingestion_id: UUID
    detected_columns: list[str]
    possible_mapping: dict[str, str]
    sample_rows: list[CsvPreviewRow]
    validation_errors: list[str]
    row_count: int
