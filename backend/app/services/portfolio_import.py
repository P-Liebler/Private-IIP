"""Raw-first transaction CSV preview and all-or-nothing commit."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from typing import cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Transaction
from app.schemas.portfolio import TransactionInput
from app.services.csv_preview import CsvPreviewService
from app.services.portfolio_engine import ledger_state
from app.services.portfolios import PortfolioService, transaction_fingerprint
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

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


async def parse_rows(
    data: bytes, account_id: UUID, mapping: dict[str, str], db: AsyncSession, account_name: str
) -> list[dict[str, object]]:
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AppError(422, "CSV_ENCODING_INVALID", "CSV must be UTF-8") from error
    reader = csv.DictReader(StringIO(decoded, newline=""), strict=True)
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
                )._resolve(identifiers, trade_date, errors)
                if status != "RESOLVED" or (
                    normalized.get("instrument_id")
                    and str(normalized["instrument_id"]) != str(instrument_id)
                ):
                    results.append(
                        {"line": line, "error": f"Identifier {status}; explicit review required"}
                    )
                    continue
                normalized["instrument_id"] = instrument_id
            payload = TransactionInput.model_validate(normalized)
            results.append({"line": line, "payload": payload})
        except ValidationError as error:
            results.append({"line": line, "error": str(error.errors()[0]["msg"])})
    if not results:
        raise AppError(422, "CSV_EMPTY", "CSV contains no transactions")
    return results


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
            },
        )
        try:
            header = next(csv.reader(StringIO(data.decode("utf-8-sig"), newline="")))
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
        rows = await parse_rows(data, account_id, proposed, self.db, account.name)
        existing = list(
            (
                await self.db.scalars(
                    select(Transaction).where(
                        Transaction.account_id == account_id, Transaction.status == "ACTIVE"
                    )
                )
            ).all()
        )
        ids = {row.external_id for row in existing if row.external_id}
        fingerprints = {row.fingerprint for row in existing}
        seen_ids: set[str] = set()
        seen_fingerprints: set[str] = set()
        preview_rows: list[dict[str, object]] = []
        for entry in rows:
            line = entry["line"]
            if "error" in entry:
                preview_rows.append({"line": line, "status": "INVALID", "error": entry["error"]})
                continue
            payload = entry["payload"]
            assert isinstance(payload, TransactionInput)
            fingerprint = transaction_fingerprint(payload)
            duplicate = (
                payload.external_id in ids | seen_ids
                if payload.external_id
                else fingerprint in fingerprints | seen_fingerprints
            )
            try:
                await self.portfolios._validate_input(portfolio_id, payload)
                if not duplicate:
                    candidate = Transaction(
                        id=UUID(int=cast(int, line)),
                        portfolio_id=portfolio_id,
                        **payload.model_dump(),
                        created_at=datetime.now(UTC),
                        voided_at=None,
                    )
                    ledger_state([*existing, candidate], date.max, datetime.now(UTC))
                    existing.append(candidate)
            except AppError as error:
                preview_rows.append({"line": line, "status": "INVALID", "error": error.message})
                continue
            preview_rows.append(
                {
                    "line": line,
                    "status": "DUPLICATE" if duplicate else "READY",
                    "type": payload.type,
                    "trade_date": payload.trade_date,
                    "instrument_id": payload.instrument_id,
                    "currency": payload.currency,
                }
            )
            if payload.external_id:
                seen_ids.add(payload.external_id)
            seen_fingerprints.add(fingerprint)
        return {
            "raw_ingestion_id": raw.id,
            "mapping": proposed,
            "columns": header,
            "row_count": len(rows),
            "rows": preview_rows,
            "ready_count": sum(row["status"] == "READY" for row in preview_rows),
        }

    async def commit(
        self, portfolio_id: UUID, account_id: UUID, raw_id: UUID, mapping: dict[str, str]
    ) -> dict[str, object]:
        await self.portfolios.owned(portfolio_id)
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
            raise AppError(409, "IMPORT_ALREADY_COMMITTED", "CSV import was already committed")
        rows = await parse_rows(data, account_id, mapping, self.db, account.name)
        if any("error" in row for row in rows):
            raise AppError(422, "CSV_ROW_INVALID", "Fix invalid rows before commit")
        created: list[str] = []
        try:
            for entry in rows:
                payload = entry["payload"]
                assert isinstance(payload, TransactionInput)
                row = await self.portfolios.create_transaction(
                    portfolio_id, payload, raw_id=raw_id, source="MANUAL_CSV", commit=False
                )
                created.append(str(row.id))
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return {
            "raw_ingestion_id": raw_id,
            "created_count": len(created),
            "transaction_ids": created,
        }
