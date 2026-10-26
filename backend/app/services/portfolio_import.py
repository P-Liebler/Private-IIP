"""Raw-first transaction CSV preview and all-or-nothing commit."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, date, datetime
from io import StringIO
from typing import cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Instrument, Transaction
from app.schemas.portfolio import TransactionInput
from app.services.csv_preview import CsvPreviewService
from app.services.portfolio_engine import ledger_state
from app.services.portfolios import PortfolioService, transaction_fingerprint
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService
from app.services.transaction_csv_format import (
    TransactionCsvFormat,
    detect_format,
    normalize_cell,
)

FIELDS = {
    "type",
    "trade_date",
    "settlement_date",
    "instrument_id",
    "quantity",
    "price",
    "amount",
    "currency",
    "fee",
    "tax",
    "external_id",
    "notes",
    "fx_rate_to_base",
    "ticker",
    "isin",
    "figi",
    "account",
}
ALIASES = {
    "date": "trade_date",
    "datum": "trade_date",
    "action": "type",
    "symbol_id": "instrument_id",
    "shares": "quantity",
    "qty": "quantity",
    "value": "amount",
    "ccy": "currency",
    "fees": "fee",
    "taxes": "tax",
    "symbol": "ticker",
    "account_name": "account",
}


def plan_hash(
    mapping: dict[str, str] | None,
    resolutions: dict[int, UUID] | None,
    csv_format: TransactionCsvFormat | None = None,
) -> str:
    value: dict[str, object] = {
        "mapping": mapping,
        "resolutions": {str(k): str(v) for k, v in (resolutions or {}).items()},
    }
    if csv_format is not None:
        value["format"] = csv_format.model_dump()
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def parse_rows(
    data: bytes,
    account_id: UUID,
    mapping: dict[str, str],
    db: AsyncSession,
    account_name: str,
    resolutions: dict[int, UUID] | None = None,
    csv_format: TransactionCsvFormat | None = None,
) -> list[dict[str, object]]:
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AppError(422, "CSV_ENCODING_INVALID", "CSV must be UTF-8") from error
    config = csv_format or detect_format(data)
    if config is None:
        raise AppError(422, "CSV_FORMAT_REQUIRED", "Select delimiter, date and number format")
    reader = csv.DictReader(StringIO(decoded, newline=""), strict=True, delimiter=config.delimiter)
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise AppError(422, "CSV_HEADERS_INVALID", "Missing or duplicate CSV headers")
    if set(mapping) - set(reader.fieldnames) or set(mapping.values()) - FIELDS:
        raise AppError(422, "CSV_MAPPING_INVALID", "Unknown mapping field")
    if len(set(mapping.values())) != len(mapping):
        raise AppError(422, "CSV_MAPPING_INVALID", "Duplicate canonical field")
    if not {"type", "trade_date", "currency"}.issubset(set(mapping.values())):
        raise AppError(422, "CSV_MAPPING_INVALID", "Type, trade date and currency are required")
    try:
        csv_rows = list(reader)
    except csv.Error as error:
        raise AppError(422, "CSV_ROW_INVALID", "Malformed CSV") from error
    results: list[dict[str, object]] = []
    for line, row in enumerate(csv_rows, start=2):
        if line > 10001:
            raise AppError(413, "CSV_ROW_LIMIT", "CSV exceeds 10000 rows")
        if None in row or any(value is None for value in row.values()):
            raise AppError(422, "CSV_ROW_INVALID", f"Extra columns on line {line}")
        normalized: dict[str, object] = {"account_id": account_id}
        for original, canonical in mapping.items():
            value = row.get(original)
            if value is not None and value.strip():
                normalized[canonical] = value.strip()
        try:
            for key in list(normalized):
                if key != "account_id":
                    normalized[key] = normalize_cell(key, str(normalized[key]), config)
            account = normalized.pop("account", None)
            if account is not None and account not in {str(account_id), account_name}:
                results.append({"line": line, "error": "CSV account differs from selected account"})
                continue
            identifiers: dict[str, str | None] = {
                key: str(normalized.pop(key))
                for key in ("ticker", "isin", "figi")
                if key in normalized
            }
            if identifiers:
                errors: list[str] = []
                try:
                    trade_date = date.fromisoformat(str(normalized.get("trade_date", "")))
                except ValueError:
                    results.append({"line": line, "error": "Invalid trade date"})
                    continue
                instrument_id, status = await CsvPreviewService(
                    db, RawIngestionService(db)
                )._resolve(identifiers, trade_date, errors, (resolutions or {}).get(line))
                if status != "RESOLVED" or (
                    normalized.get("instrument_id")
                    and str(normalized["instrument_id"]) != str(instrument_id)
                ):
                    results.append(
                        {"line": line, "error": f"Identifier {status}; explicit review required"}
                    )
                    continue
                normalized["instrument_id"] = instrument_id
            elif line in (resolutions or {}):
                selected = (resolutions or {})[line]
                if normalized.get("instrument_id") and str(normalized["instrument_id"]) != str(
                    selected
                ):
                    results.append(
                        {"line": line, "error": "Selected instrument conflicts with CSV ID"}
                    )
                    continue
                normalized["instrument_id"] = selected
            payload = TransactionInput.model_validate(normalized)
            results.append({"line": line, "payload": payload})
        except ValidationError as error:
            results.append({"line": line, "error": str(error.errors()[0]["msg"])})
        except ValueError:
            results.append({"line": line, "error": "Date or number does not match selected format"})
    if not results:
        raise AppError(422, "CSV_EMPTY", "CSV contains no transactions")
    return results


def duplicate_status(payload: TransactionInput, existing: list[Transaction]) -> str:
    """Include voided originals: reimport must never resurrect a correction."""
    fingerprint = transaction_fingerprint(payload)
    if payload.external_id:
        matches = [row for row in existing if row.external_id == payload.external_id]
        if matches:
            return (
                "DUPLICATE"
                if any(row.fingerprint == fingerprint for row in matches)
                else "CONFLICT"
            )
        return "NEW"
    return "DUPLICATE" if any(row.fingerprint == fingerprint for row in existing) else "NEW"


class PortfolioImportService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.portfolios = PortfolioService(db, user_id)
        self.raw = RawIngestionService(db)

    async def preview(
        self,
        portfolio_id: UUID,
        account_id: UUID,
        data: bytes,
        filename: str,
        mapping: dict[str, str] | None = None,
        resolutions: dict[int, UUID] | None = None,
        csv_format: TransactionCsvFormat | None = None,
    ) -> dict[str, object]:
        await self.portfolios.owned(portfolio_id)
        account = await self.portfolios.account(portfolio_id, account_id)
        source = await SourceService(self.db).get("MANUAL_CSV")
        SourceGate.require_enabled(source, "manual_upload")
        if not data or len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV must be between 1 byte and 5 MB")
        raw = await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="portfolio_transaction_csv",
            content_type="text/csv",
            request_metadata={
                "filename": filename,
                "user_id": str(self.user_id),
                "portfolio_id": str(portfolio_id),
                "account_id": str(account_id),
                "parser_version": "PR6_TRANSACTION_CSV_V2",
                "request_key": plan_hash(mapping, resolutions, csv_format),
                "csv_format": csv_format.model_dump_json() if csv_format else "AUTO",
            },
        )
        config = csv_format or detect_format(data)
        if config is None:
            return {
                "raw_ingestion_id": raw.id,
                "mapping": mapping or {},
                "columns": [],
                "row_count": 0,
                "ready_count": 0,
                "format_required": True,
                "rows": [
                    {
                        "line": 1,
                        "status": "FORMAT_REQUIRED",
                        "error": "Select delimiter, date order and decimal notation explicitly",
                    }
                ],
            }
        try:
            header = next(
                csv.reader(
                    StringIO(data.decode("utf-8-sig"), newline=""), delimiter=config.delimiter
                )
            )
        except (UnicodeDecodeError, StopIteration, csv.Error) as error:
            raise AppError(422, "CSV_HEADERS_INVALID", "Invalid CSV headers") from error
        proposed = (
            mapping
            if mapping is not None
            else {
                column: ALIASES.get(column.strip().lower(), column.strip().lower())
                for column in header
                if ALIASES.get(column.strip().lower(), column.strip().lower()) in FIELDS
            }
        )
        if not {"type", "trade_date", "currency"}.issubset(set(proposed.values())) or len(
            set(proposed.values())
        ) != len(proposed):
            return {
                "raw_ingestion_id": raw.id,
                "mapping": proposed,
                "columns": header,
                "row_count": 0,
                "ready_count": 0,
                "mapping_required": True,
                "rows": [
                    {
                        "line": 1,
                        "status": "MAPPING_REQUIRED",
                        "error": "Map type, trade_date and currency uniquely before validation",
                    }
                ],
            }
        rows = await parse_rows(
            data, account_id, proposed, self.db, account.name, resolutions, config
        )
        existing = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.account_id == account_id)
                )
            ).all()
        )
        preview_rows: list[dict[str, object]] = []
        for entry in rows:
            line = entry["line"]
            if "error" in entry:
                preview_rows.append({"line": line, "status": "INVALID", "error": entry["error"]})
                continue
            payload = entry["payload"]
            assert isinstance(payload, TransactionInput)
            fingerprint = transaction_fingerprint(payload)
            classification = duplicate_status(payload, existing)
            duplicate = classification == "DUPLICATE"
            if classification == "CONFLICT":
                preview_rows.append(
                    {
                        "line": line,
                        "status": "CONFLICT",
                        "error": (
                            "External ID has different accounting values; "
                            "review correction explicitly"
                        ),
                    }
                )
                continue
            try:
                await self.portfolios._validate_input(portfolio_id, payload)
                if not duplicate:
                    candidate = Transaction(
                        id=UUID(int=cast(int, line)),
                        portfolio_id=portfolio_id,
                        **payload.model_dump(),
                        created_at=datetime.now(UTC),
                        voided_at=None,
                        fingerprint=fingerprint,
                    )
                    ledger_state([*existing, candidate], date.max, datetime.now(UTC))
                    existing.append(candidate)
            except AppError as error:
                preview_rows.append({"line": line, "status": "INVALID", "error": error.message})
                continue
            instrument = (
                await self.db.get(Instrument, payload.instrument_id)
                if payload.instrument_id
                else None
            )
            preview_rows.append(
                {
                    "line": line,
                    "status": "DUPLICATE" if duplicate else "READY",
                    **payload.model_dump(mode="json"),
                    "instrument_name": instrument.name if instrument else None,
                }
            )
        return {
            "raw_ingestion_id": raw.id,
            "mapping": proposed,
            "columns": header,
            "row_count": len(rows),
            "detected_format": config.model_dump(),
            "rows": preview_rows,
            "ready_count": sum(row["status"] == "READY" for row in preview_rows),
            "duplicate_count": sum(row["status"] == "DUPLICATE" for row in preview_rows),
            "instrument_resolutions": {str(k): str(v) for k, v in (resolutions or {}).items()},
        }

    async def commit(
        self,
        portfolio_id: UUID,
        account_id: UUID,
        raw_id: UUID,
        mapping: dict[str, str],
        resolutions: dict[int, UUID] | None = None,
        csv_format: TransactionCsvFormat | None = None,
    ) -> dict[str, object]:
        await self.portfolios.owned(portfolio_id, lock=True)
        account = await self.portfolios.account(portfolio_id, account_id)
        raw = await self.raw.get(raw_id)
        if (
            raw.resource_type != "portfolio_transaction_csv"
            or raw.request_metadata.get("user_id") != str(self.user_id)
            or raw.request_metadata.get("portfolio_id") != str(portfolio_id)
            or raw.request_metadata.get("account_id") != str(account_id)
        ):
            raise AppError(404, "IMPORT_NOT_FOUND", "Transaction import not found")
        source = await SourceService(self.db).get("MANUAL_CSV")
        SourceGate.require_enabled(source, "manual_upload")
        data = await self.raw.get_verified(raw_id)
        if await self.db.scalar(
            select(Transaction.id).where(Transaction.raw_ingestion_id == raw_id)
        ):
            return {
                "raw_ingestion_id": raw_id,
                "created_count": 0,
                "transaction_ids": [],
                "status": "ALREADY_COMMITTED",
            }
        recorded_plan = raw.request_metadata.get("request_key")
        config = csv_format or detect_format(data)
        if config is None:
            raise AppError(409, "CSV_FORMAT_REQUIRED", "Preview an explicit format before commit")
        if recorded_plan == plan_hash(None, resolutions, csv_format):
            header = next(
                csv.reader(
                    StringIO(data.decode("utf-8-sig"), newline=""), delimiter=config.delimiter
                )
            )
            automatic = {
                column: ALIASES.get(column.strip().lower(), column.strip().lower())
                for column in header
                if ALIASES.get(column.strip().lower(), column.strip().lower()) in FIELDS
            }
            valid_plan = automatic == mapping
        else:
            valid_plan = recorded_plan == plan_hash(mapping, resolutions, csv_format)
        version = raw.request_metadata.get("parser_version")
        if version not in {"PR5_TRANSACTION_CSV_V1", "PR6_TRANSACTION_CSV_V2"} or not valid_plan:
            raise AppError(
                409,
                "IMPORT_PREVIEW_CHANGED",
                "Preview changed columns and instrument choices before commit",
            )
        rows = await parse_rows(
            data, account_id, mapping, self.db, account.name, resolutions, config
        )
        if any("error" in row for row in rows):
            raise AppError(422, "CSV_ROW_INVALID", "Fix invalid rows before commit")
        created: list[str] = []
        skipped = 0
        existing = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.account_id == account_id)
                )
            ).all()
        )
        try:
            for entry in rows:
                payload = entry["payload"]
                assert isinstance(payload, TransactionInput)
                classification = duplicate_status(payload, existing)
                if classification == "CONFLICT":
                    raise AppError(
                        409,
                        "IMPORT_ID_CONFLICT",
                        "External ID differs; use explicit transaction correction",
                    )
                if classification == "DUPLICATE":
                    skipped += 1
                    continue
                row = await self.portfolios.create_transaction(
                    portfolio_id, payload, raw_id=raw_id, source="MANUAL_CSV", commit=False
                )
                created.append(str(row.id))
                existing.append(row)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return {
            "raw_ingestion_id": raw_id,
            "created_count": len(created),
            "duplicate_count": skipped,
            "transaction_ids": created,
        }
