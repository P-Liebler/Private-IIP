from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from io import StringIO
from typing import cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataQuarantine, Filing, FundamentalFact, Instrument, RawIngestion
from app.schemas.research import FactInput
from app.services.audit import audit_service
from app.services.market_queries import pit_cutoff
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

RULE_VERSION = "fundamentals-v1"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def fact_key(fact: FactInput | FundamentalFact) -> tuple[object, ...]:
    return (fact.instrument_id, fact.metric, fact.period_start, fact.period_end, fact.period_type)


def fact_view(fact: FundamentalFact) -> dict[str, object]:
    return {
        name: getattr(fact, name)
        for name in (
            "id",
            "instrument_id",
            "metric",
            "value",
            "unit",
            "currency",
            "period_start",
            "period_end",
            "period_type",
            "fiscal_year",
            "fiscal_quarter",
            "filing_id",
            "source_id",
            "raw_ingestion_id",
            "known_at",
            "observed_at",
            "retrieved_at",
            "validation_status",
            "quality_score",
            "quality_components",
            "parser_version",
            "rule_version",
            "replaces_version_id",
            "evidence",
        )
    }


class FundamentalService:
    def __init__(self, db: AsyncSession, raw: RawIngestionService | None = None) -> None:
        self.db = db
        self.raw = raw or RawIngestionService(db)

    async def get_fundamentals(
        self, instrument_id: UUID, as_of: datetime | None = None
    ) -> list[FundamentalFact]:
        cutoff = pit_cutoff(as_of)
        rows = (
            await self.db.scalars(
                select(FundamentalFact)
                .where(
                    FundamentalFact.instrument_id == instrument_id,
                    FundamentalFact.known_at <= cutoff,
                    FundamentalFact.observed_at <= cutoff,
                    FundamentalFact.period_end <= cutoff.date(),
                )
                .order_by(
                    FundamentalFact.known_at.desc(),
                    FundamentalFact.observed_at.desc(),
                    FundamentalFact.id.desc(),
                )
            )
        ).all()
        grouped: dict[tuple[object, ...], FundamentalFact] = {}
        for row in rows:
            # A rejected later observation must not replace a verified canonical fact.
            if row.validation_status != "REJECTED":
                grouped.setdefault(fact_key(row), row)
        return list(grouped.values())

    async def persist(
        self,
        inputs: list[FactInput],
        raw: RawIngestion,
        *,
        parser: str,
        filings: dict[str, Filing] | None = None,
    ) -> dict[str, int]:
        if raw.status != "STORED":
            raise AppError(409, "RAW_NOT_AVAILABLE", "Stored raw evidence required")
        inserted, unchanged, restated = 0, 0, 0
        for item in inputs:
            instrument = await self.db.get(Instrument, item.instrument_id, with_for_update=True)
            if instrument is None:
                raise AppError(422, "INSTRUMENT_NOT_FOUND", "Unknown instrument")
            key = digest((*fact_key(item), item.filing_reference))
            existing_raw = (
                await self.db.scalars(
                    select(FundamentalFact).where(
                        FundamentalFact.raw_ingestion_id == raw.id, FundamentalFact.row_key == key
                    )
                )
            ).one_or_none()
            if existing_raw:
                unchanged += 1
                continue
            previous = (
                await self.db.scalars(
                    select(FundamentalFact)
                    .where(
                        FundamentalFact.instrument_id == item.instrument_id,
                        FundamentalFact.metric == item.metric,
                        FundamentalFact.period_start == item.period_start,
                        FundamentalFact.period_end == item.period_end,
                        FundamentalFact.period_type == item.period_type,
                        FundamentalFact.validation_status != "REJECTED",
                    )
                    .order_by(FundamentalFact.observed_at.desc(), FundamentalFact.id.desc())
                    .limit(1)
                )
            ).one_or_none()
            known = item.known_at or raw.received_at
            if known > raw.received_at or item.period_end > raw.received_at.date():
                raise AppError(422, "FUTURE_RELEASE", "Release cannot follow ingestion")
            warnings: list[str] = []
            source_conflict = bool(
                previous and previous.source_id != raw.source_id and previous.value != item.value
            )
            context_conflict = bool(
                previous and (previous.unit != item.unit or previous.currency != item.currency)
            )
            if source_conflict:
                warnings.append("SOURCE_CONFLICT_REQUIRES_REVIEW")
            if context_conflict:
                warnings.append("CONTEXT_CONFLICT_REQUIRES_REVIEW")
            if (
                previous
                and previous.value != item.value
                and not (source_conflict or context_conflict)
            ):
                warnings.append("RESTATEMENT")
                restated += 1
                if previous.value and abs(item.value / previous.value - 1) > 0.5:
                    warnings.append("LARGE_CHANGE")
            if not item.known_at:
                warnings.append("LOCAL_RECEIPT_ONLY")
            filing = (filings or {}).get(item.filing_reference)
            fields = item.model_dump(
                exclude={
                    "filing_reference",
                    "known_at",
                    "availability_evidence",
                    "share_class",
                    "split_basis_date",
                    "consolidated",
                }
            )
            row = FundamentalFact(
                **fields,
                source_id=raw.source_id,
                raw_ingestion_id=raw.id,
                row_key=key,
                known_at=known,
                observed_at=raw.received_at,
                retrieved_at=raw.received_at,
                filing_id=filing.id if filing else None,
                parser_version=parser,
                rule_version=RULE_VERSION,
                replaces_version_id=previous.id if previous else None,
                validation_status=(
                    "REJECTED"
                    if source_conflict or context_conflict
                    else "WARNING"
                    if warnings
                    else "VALID"
                ),
                quality_score=None
                if source_conflict or context_conflict
                else "0.70"
                if warnings
                else "0.85",
                quality_components={
                    "schema_valid": True,
                    "single_source": True,
                    "warnings": warnings,
                    "cross_source_verified": False,
                },
                evidence={
                    "release": item.availability_evidence,
                    "filing_reference": item.filing_reference,
                    "share_class": item.share_class,
                    "split_basis_date": str(item.split_basis_date)
                    if item.split_basis_date
                    else None,
                    "consolidated": True,
                },
            )
            self.db.add(row)
            await self.db.flush()
            inserted += 1
        return {"inserted": inserted, "unchanged": unchanged, "restated": restated}

    async def upload(self, data: bytes, filename: str, user_id: UUID) -> dict[str, object]:
        source = await SourceService(self.db).get("MANUAL_RESEARCH")
        SourceGate.require_enabled(source, "fundamentals")
        if not data or len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "Upload must be 1 byte to 5 MB")
        raw = await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="fundamental_csv",
            content_type="text/csv",
            request_metadata={"filename": filename, "user_id": str(user_id)},
        )
        return await self.preview(raw.id, {}, user_id)

    async def parse_csv(
        self, raw_id: UUID, mapping: dict[str, str], user_id: UUID
    ) -> tuple[RawIngestion, list[FactInput], list[dict[str, object]], list[str]]:
        raw = await self.raw.get(raw_id)
        if raw.resource_type != "fundamental_csv" or raw.request_metadata.get("user_id") != str(
            user_id
        ):
            raise AppError(403, "IMPORT_FORBIDDEN", "Import belongs to another user")
        source = await SourceService(self.db).get("MANUAL_RESEARCH")
        SourceGate.require_enabled(source, "fundamentals")
        if source.id != raw.source_id:
            raise AppError(409, "SOURCE_MISMATCH", "Unexpected raw source")
        data = await self.raw.get_verified(raw_id)
        try:
            reader = csv.DictReader(StringIO(data.decode("utf-8-sig")))
            headers = list(reader.fieldnames or [])
            if len(set(headers)) != len(headers):
                raise ValueError("Duplicate columns")
            inputs: list[FactInput] = []
            errors: list[dict[str, object]] = []
            keys: set[tuple[object, ...]] = set()
            for line, source_row in enumerate(reader, 2):
                if line > 10001:
                    raise ValueError("At most 10000 rows")
                row = {
                    mapping.get(key, key): value
                    for key, value in source_row.items()
                    if key is not None and value not in (None, "")
                }
                try:
                    item = FactInput.model_validate(row)
                    if fact_key(item) in keys:
                        raise ValueError("Ambiguous duplicate metric/period")
                    if await self.db.get(Instrument, item.instrument_id) is None:
                        raise ValueError("Unknown instrument")
                    if item.known_at and item.known_at > raw.received_at:
                        raise ValueError("Future release")
                    keys.add(fact_key(item))
                    inputs.append(item)
                except (ValidationError, ValueError):
                    errors.append(
                        {
                            "line": line,
                            "reason": "Invalid fact, identity, unit, period or release evidence",
                        }
                    )
            if not inputs and not errors:
                errors.append({"line": 1, "reason": "No rows"})
            return raw, inputs, errors, headers
        except (UnicodeDecodeError, csv.Error, ValueError) as error:
            raise AppError(422, "CSV_INVALID", "Invalid UTF-8 CSV or row limit") from error

    async def preview(
        self, raw_id: UUID, mapping: dict[str, str], user_id: UUID
    ) -> dict[str, object]:
        raw, inputs, errors, headers = await self.parse_csv(raw_id, mapping, user_id)
        for error in errors:
            line = int(str(error["line"]))
            exists = await self.db.scalar(
                select(DataQuarantine.id).where(
                    DataQuarantine.raw_ingestion_id == raw.id,
                    DataQuarantine.row_number == line,
                    DataQuarantine.data_type == "fundamental",
                )
            )
            if not exists:
                self.db.add(
                    DataQuarantine(
                        raw_ingestion_id=raw.id,
                        source_id=raw.source_id,
                        row_number=line,
                        data_type="fundamental",
                        record_key=f"line:{line}",
                        reason=str(error["reason"]),
                        severity="ERROR",
                        row_data={},
                    )
                )
        await self.db.commit()
        return {
            "raw_ingestion_id": raw.id,
            "columns": headers,
            "mapping": mapping,
            "rows": [item.model_dump(mode="json") for item in inputs[:100]],
            "errors": errors,
            "valid_rows": len(inputs),
            "can_commit": bool(inputs) and not errors,
        }

    async def commit(self, raw_id: UUID, mapping: dict[str, str], user_id: UUID) -> dict[str, int]:
        raw, inputs, errors, _ = await self.parse_csv(raw_id, mapping, user_id)
        if errors or not inputs:
            raise AppError(422, "IMPORT_INVALID", "Fix all invalid rows before committing")
        try:
            result = await self.persist(inputs, raw, parser="manual-fundamental-csv-v1")
            audit_service.record(
                self.db,
                event="research.imported",
                resource="raw_ingestion",
                resource_id=str(raw.id),
                actor_user_id=user_id,
                metadata=cast(dict[str, str | int | bool | None], result),
            )
            await self.db.commit()
            return result
        except Exception:
            await self.db.rollback()
            raise
