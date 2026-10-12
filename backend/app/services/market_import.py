from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    CorporateAction,
    CorporateActionVersion,
    DataQuarantine,
    DataSource,
    FxRate,
    FxRateVersion,
    Instrument,
    PriceDaily,
    PriceDailyVersion,
)
from app.services.audit import audit_service
from app.services.csv_preview import CsvPreviewService
from app.services.market_validation import (
    PARSER_VERSION,
    RECONCILIATION_VERSION,
    VALIDATION_VERSION,
    discrepancy,
    quality_score,
    validate_action,
    validate_fx,
    validate_price,
)
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

FIELDS = {
    "prices": {
        "date",
        "ticker",
        "isin",
        "figi",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "currency",
        "adjusted_close",
    },
    "actions": {
        "date",
        "ticker",
        "isin",
        "figi",
        "action_type",
        "value",
        "ratio",
        "cash_amount",
        "record_date",
        "payment_date",
        "currency",
        "new_ticker",
    },
    "fx": {"date", "base_currency", "quote_currency", "rate"},
}
REQUIRED = {
    "prices": {"date", "close"},
    "actions": {"date", "action_type"},
    "fx": {"date", "base_currency", "quote_currency", "rate"},
}


@dataclass
class ParsedRow:
    line: int
    raw: dict[str, str | None]
    values: dict[str, object]
    instrument_id: UUID | None
    errors: list[str]
    warnings: list[str]

    def view(self) -> dict[str, object]:
        return {
            "line": self.line,
            "values": self.raw,
            "normalized": {
                key: value.isoformat()
                if isinstance(value, date)
                else str(value)
                if isinstance(value, Decimal)
                else value
                for key, value in self.values.items()
            },
            "instrument_id": self.instrument_id,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class MarketImportService:
    def __init__(self, db: AsyncSession, raw: RawIngestionService | None = None) -> None:
        self.db = db
        self.raw = raw or RawIngestionService(db)
        self.actor_user_id: UUID | None = None

    async def preview(self, kind: str, data: bytes, filename: str) -> dict[str, object]:
        self._kind(kind)
        source = await SourceService(self.db).get("MANUAL_CSV")
        SourceGate.require_enabled(source, "manual_upload")
        if not data or len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV must be between 1 byte and 5 MB")
        raw = await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type=f"manual_{kind}_csv",
            content_type="text/csv",
            request_metadata={"filename": filename},
        )
        rows, errors, mapping = await self._parse(kind, data, None)
        return self._summary(raw.id, rows, errors, mapping)

    async def commit(
        self,
        kind: str,
        raw_id: UUID,
        mapping: dict[str, str],
        *,
        accept_partial: bool = False,
        conflict_policy: str = "REJECT",
        decision_note: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> dict[str, object]:
        self._kind(kind)
        self.actor_user_id = actor_user_id
        source = await SourceService(self.db).get("MANUAL_CSV")
        SourceGate.require_enabled(source, "manual_upload")
        raw = await self.raw.get(raw_id)
        if raw.resource_type != f"manual_{kind}_csv" or raw.source_id != source.id:
            raise AppError(
                422, "IMPORT_RAW_MISMATCH", "Raw object does not match import type and source"
            )
        data = await self.raw.get_verified(raw_id)
        rows, errors, detected_mapping = await self._parse(kind, data, mapping)
        if errors:
            raise AppError(422, "CSV_INVALID", "; ".join(errors[:5]))
        if mapping != detected_mapping:
            raise AppError(422, "MAPPING_MISMATCH", "Confirmed mapping does not match CSV columns")
        invalid = [row for row in rows if row.errors]
        if invalid and not accept_partial:
            raise AppError(
                422, "ROWS_INVALID", "Invalid rows require explicit partial-import confirmation"
            )
        if conflict_policy not in {"REJECT", "ACCEPT_NEW", "KEEP_EXISTING"}:
            raise AppError(422, "CONFLICT_POLICY_INVALID", "Unknown conflict policy")
        if conflict_policy != "REJECT" and (not decision_note or not decision_note.strip()):
            raise AppError(422, "DECISION_NOTE_REQUIRED", "Conflict resolution requires a reason")
        result = {
            "inserted": 0,
            "corrected": 0,
            "observed_only": 0,
            "unchanged": 0,
            "quarantined": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "new_versions": 0,
        }
        try:
            # Serialize one raw commit and protect current pointers from concurrent writers.
            await self.db.execute(select(type(raw)).where(type(raw).id == raw_id).with_for_update())
            await self.db.execute(
                text(
                    "LOCK TABLE price_daily, corporate_actions, fx_rates "
                    "IN SHARE ROW EXCLUSIVE MODE"
                )
            )
            for row in rows:
                if row.errors:
                    existing_q = await self.db.scalar(
                        select(DataQuarantine.id).where(
                            DataQuarantine.raw_ingestion_id == raw_id,
                            DataQuarantine.row_number == row.line,
                            DataQuarantine.data_type == kind,
                        )
                    )
                    if existing_q is None:
                        self.db.add(
                            DataQuarantine(
                                raw_ingestion_id=raw_id,
                                source_id=source.id,
                                instrument_id=row.instrument_id,
                                row_number=row.line,
                                data_type=kind,
                                record_key=str(
                                    row.values.get("trading_date")
                                    or row.values.get("action_date")
                                    or row.values.get("rate_date")
                                    or row.line
                                ),
                                reason="; ".join(row.errors),
                                severity="REJECTED",
                                row_data=row.raw,
                            )
                        )
                        result["quarantined"] += 1
                        result["rejected_rows"] += 1
                    else:
                        result["unchanged"] += 1
                elif kind == "prices":
                    await self._price(
                        row,
                        raw_id,
                        source.id,
                        source.trust_level,
                        source.priority,
                        raw.received_at,
                        conflict_policy,
                        decision_note,
                        result,
                    )
                elif kind == "actions":
                    await self._action(row, raw_id, source.id, raw.received_at, result)
                else:
                    await self._fx(
                        row,
                        raw_id,
                        source.id,
                        source.priority,
                        raw.received_at,
                        conflict_policy,
                        result,
                    )
            audit_service.record(
                self.db,
                event={
                    "prices": "market.price_import_committed",
                    "actions": "market.corporate_action_import_committed",
                    "fx": "fx.import_committed",
                }[kind],
                resource="raw_ingestion",
                resource_id=str(raw_id),
                actor_user_id=actor_user_id,
                metadata={
                    "inserted": result["inserted"],
                    "corrected": result["corrected"],
                    "quarantined": result["quarantined"],
                },
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return {
            "raw_ingestion_id": raw_id,
            "accepted_rows": result["inserted"] + result["corrected"],
            **result,
        }

    async def _parse(
        self, kind: str, data: bytes, mapping: dict[str, str] | None
    ) -> tuple[list[ParsedRow], list[str], dict[str, str]]:
        errors: list[str] = []
        try:
            reader = csv.DictReader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
            columns = reader.fieldnames or []
        except (UnicodeDecodeError, csv.Error):
            return [], ["CSV must be valid UTF-8 with a header"], {}
        if not columns or len(columns) != len(set(columns)):
            return [], ["CSV columns must be unique"], {}
        expected = (
            mapping
            if mapping is not None
            else {
                column: {"ex_date": "date", "type": "action_type"}.get(
                    column.strip().lower(), column.strip().lower()
                )
                for column in columns
            }
        )
        if (
            set(expected) != set(columns)
            or len(set(expected.values())) != len(expected)
            or any(name not in FIELDS[kind] for name in expected.values())
        ):
            return [], ["Invalid or incomplete CSV column mapping"], expected
        if not REQUIRED[kind] <= set(expected.values()):
            errors.append(
                "Missing required columns: "
                + ", ".join(sorted(REQUIRED[kind] - set(expected.values())))
            )
        if kind != "fx" and not {"ticker", "isin", "figi"} & set(expected.values()):
            errors.append("Missing instrument identifier column")
        rows: list[ParsedRow] = []
        keys: set[tuple[object, ...]] = set()
        try:
            for line, source_row in enumerate(reader, 2):
                if line > 10001:
                    errors.append("Maximum 10000 rows")
                    break
                normalized = {
                    canonical: source_row.get(original) for original, canonical in expected.items()
                }
                row_errors: list[str] = []
                warnings: list[str] = []
                values: dict[str, object] = {}
                instrument_id: UUID | None = None
                if None in source_row or any(value is None for value in source_row.values()):
                    row_errors.append("Malformed CSV row")
                if kind != "fx":
                    try:
                        as_of = date.fromisoformat(normalized.get("date") or "")
                    except ValueError:
                        as_of = None
                    instrument_id, status = await CsvPreviewService(self.db, self.raw)._resolve(
                        normalized, as_of, row_errors
                    )
                    if status != "RESOLVED":
                        row_errors.append("Instrument " + status)
                instrument = await self.db.get(Instrument, instrument_id) if instrument_id else None
                try:
                    if kind == "prices":
                        values, warnings = validate_price(
                            normalized, instrument.currency if instrument else ""
                        )
                    elif kind == "actions":
                        values = validate_action(
                            normalized, instrument.currency if instrument else ""
                        )
                    else:
                        values = validate_fx(normalized)
                except ValueError as error:
                    row_errors.append(str(error))
                if values:
                    key = (
                        instrument_id,
                        values.get("trading_date")
                        or values.get("action_date")
                        or values.get("rate_date"),
                        values.get("action_type")
                        if kind == "actions"
                        else values.get("base_currency"),
                        values.get("quote_currency"),
                    )
                    if key in keys:
                        row_errors.append("Duplicate key in CSV")
                    keys.add(key)
                rows.append(
                    ParsedRow(line, normalized, values, instrument_id, row_errors, warnings)
                )
        except csv.Error:
            errors.append("Malformed CSV structure")
        if not rows:
            errors.append("CSV contains no data rows")
        return rows, errors, expected

    @staticmethod
    def _summary(
        raw_id: UUID, rows: list[ParsedRow], errors: list[str], mapping: dict[str, str]
    ) -> dict[str, object]:
        return {
            "raw_ingestion_id": raw_id,
            "mapping": mapping,
            "row_count": len(rows),
            "invalid_count": sum(bool(row.errors) for row in rows),
            "warnings_count": sum(bool(row.warnings) for row in rows),
            "validation_errors": errors,
            "sample_rows": [row.view() for row in rows[:50]],
        }

    @staticmethod
    def _kind(kind: str) -> None:
        if kind not in FIELDS:
            raise AppError(404, "IMPORT_TYPE_NOT_FOUND", "Unknown import type")

    async def _price(
        self,
        row: ParsedRow,
        raw_id: UUID,
        source_id: UUID,
        trust: str,
        priority: int,
        observed: datetime,
        policy: str,
        note: str | None,
        result: dict[str, int],
    ) -> None:
        assert row.instrument_id is not None
        d = row.values
        trading_date = cast(date, d["trading_date"])
        incoming_close = cast(Decimal, d["close"])
        prior_row = await self.db.get(
            PriceDaily, (row.instrument_id, trading_date), with_for_update=True
        )
        previous = await self.db.get(PriceDailyVersion, prior_row.version_id) if prior_row else None
        previous_raw = await self.db.scalar(
            select(PriceDailyVersion.id).where(
                PriceDailyVersion.raw_ingestion_id == raw_id,
                PriceDailyVersion.row_number == row.line,
            )
        )
        if previous_raw:
            result["unchanged"] += 1
            return
        crosscheck, pct = (
            discrepancy(previous.close, incoming_close)
            if previous
            else ("NO_REFERENCE", Decimal(0))
        )
        warnings = list(row.warnings)
        if crosscheck in {"NOTICE", "REVIEW", "SEVERE"}:
            warnings.append(f"CLOSE_DISCREPANCY_{crosscheck}:{pct:.4f}%")
        if previous and abs(incoming_close / previous.close - 1) > Decimal("0.20"):
            warnings.append("LARGE_CLOSE_CHANGE")
        if crosscheck == "REVIEW" and policy == "REJECT":
            raise AppError(
                409,
                "PRICE_CONFLICT_REVIEW",
                f"Row {row.line}: close discrepancy {pct:.4f}% requires explicit resolution",
            )
        prior_source = await self.db.get(DataSource, previous.source_id) if previous else None
        lower_priority = (
            previous is not None and prior_source is not None and prior_source.priority < priority
        )
        same = previous is not None and all(
            getattr(previous, key) == value for key, value in d.items() if key != "trading_date"
        )
        if same and previous is not None and previous.source_id == source_id:
            result["unchanged"] += 1
            return
        resolution = (
            "QUARANTINED"
            if crosscheck == "SEVERE" and policy == "REJECT"
            else "DUPLICATE"
            if same
            else "KEPT_EXISTING"
            if policy == "KEEP_EXISTING" and crosscheck in {"REVIEW", "SEVERE"}
            else "LOWER_PRIORITY"
            if lower_priority and policy != "ACCEPT_NEW"
            else "MANUAL_OVERRIDE"
            if crosscheck in {"REVIEW", "SEVERE"}
            else "ACCEPTED"
        )
        score, label, components = quality_score(
            trust=trust,
            complete_ohlc=all(d.get(key) is not None for key in ("open", "high", "low")),
            observed_at=observed,
            trading_date=trading_date,
            crosscheck=crosscheck,
            action_checked=False,
        )
        if note and resolution in {"MANUAL_OVERRIDE", "KEPT_EXISTING"}:
            warnings.append("DECISION:" + note.strip()[:180])
        version = PriceDailyVersion(
            instrument_id=row.instrument_id,
            **d,
            source_id=source_id,
            raw_ingestion_id=raw_id,
            row_number=row.line,
            observed_at=observed,
            known_at=datetime.now(UTC),
            retrieved_at=observed,
            validation_status="REJECTED"
            if resolution == "QUARANTINED"
            else "WARNING"
            if warnings
            else "VALID",
            parser_version=PARSER_VERSION,
            validation_version=VALIDATION_VERSION,
            reconciliation_version=RECONCILIATION_VERSION,
            replaces_version_id=previous.id
            if previous and resolution in {"ACCEPTED", "MANUAL_OVERRIDE"}
            else None,
            quality_score=score,
            quality_label=label,
            quality_components=components,
            warnings=warnings,
            resolution=resolution,
        )
        self.db.add(version)
        await self.db.flush()
        result["new_versions"] += 1
        if version.validation_status == "WARNING":
            result["warning_rows"] += 1
        if crosscheck == "SEVERE":
            self.db.add(
                DataQuarantine(
                    raw_ingestion_id=raw_id,
                    source_id=source_id,
                    instrument_id=row.instrument_id,
                    row_number=row.line,
                    data_type="prices",
                    record_key=f"{row.instrument_id}:{trading_date}",
                    reason=f"Close discrepancy {pct:.4f}%",
                    severity="REVIEW",
                    row_data=row.raw,
                    resolved_at=datetime.now(UTC) if policy != "REJECT" else None,
                    resolution=policy if policy != "REJECT" else None,
                )
            )
            result["quarantined"] += 1
            if policy != "REJECT":
                audit_service.record(
                    self.db,
                    event="quarantine.resolved",
                    resource="price_daily",
                    resource_id=str(version.id),
                    actor_user_id=self.actor_user_id,
                    metadata={"resolution": policy, "raw_ingestion_id": str(raw_id)},
                )
        audit_service.record(
            self.db,
            event="market.price_version_created",
            resource="price_daily_version",
            resource_id=str(version.id),
            actor_user_id=self.actor_user_id,
            metadata={"resolution": resolution, "raw_ingestion_id": str(raw_id)},
        )
        source_count = (
            await self.db.scalar(
                select(func.count(func.distinct(PriceDailyVersion.source_id))).where(
                    PriceDailyVersion.instrument_id == row.instrument_id,
                    PriceDailyVersion.trading_date == trading_date,
                )
            )
            or 1
        )
        if resolution in {"ACCEPTED", "MANUAL_OVERRIDE"}:
            if prior_row:
                prior_row.version_id = version.id
                for field in (
                    "open",
                    "high",
                    "low",
                    "close",
                    "adjusted_close",
                    "volume",
                    "currency",
                ):
                    setattr(prior_row, field, d[field])
                prior_row.primary_source_id = source_id
                prior_row.source_count = source_count
                prior_row.validation_status = version.validation_status
                prior_row.quality_score = score
                prior_row.quality_components = components
                result["corrected"] += 1
            else:
                self.db.add(
                    PriceDaily(
                        instrument_id=row.instrument_id,
                        trading_date=trading_date,
                        version_id=version.id,
                        **{
                            field: d[field]
                            for field in (
                                "open",
                                "high",
                                "low",
                                "close",
                                "adjusted_close",
                                "volume",
                                "currency",
                            )
                        },
                        primary_source_id=source_id,
                        source_count=source_count,
                        validation_status=version.validation_status,
                        quality_score=score,
                        quality_components=components,
                    )
                )
                result["inserted"] += 1
        else:
            if prior_row:
                prior_row.source_count = source_count
            result["observed_only"] += 1

    async def _action(
        self,
        row: ParsedRow,
        raw_id: UUID,
        source_id: UUID,
        observed: datetime,
        result: dict[str, int],
    ) -> None:
        assert row.instrument_id is not None
        d = row.values
        current = await self.db.get(
            CorporateAction,
            (row.instrument_id, d["action_date"], d["action_type"]),
            with_for_update=True,
        )
        existing = await self.db.scalar(
            select(CorporateActionVersion.id).where(
                CorporateActionVersion.raw_ingestion_id == raw_id,
                CorporateActionVersion.row_number == row.line,
            )
        )
        if existing:
            result["unchanged"] += 1
            return
        previous = (
            await self.db.get(CorporateActionVersion, current.version_id) if current else None
        )
        if previous and all(getattr(previous, key) == value for key, value in d.items()):
            result["unchanged"] += 1
            return
        source = await self.db.get(DataSource, source_id)
        assert source is not None
        score, _label, components = quality_score(
            trust=source.trust_level,
            complete_ohlc=True,
            observed_at=observed,
            trading_date=cast(date, d["action_date"]),
            crosscheck="NO_REFERENCE",
            action_checked=True,
        )
        version = CorporateActionVersion(
            instrument_id=row.instrument_id,
            **d,
            source_id=source_id,
            raw_ingestion_id=raw_id,
            row_number=row.line,
            observed_at=observed,
            known_at=datetime.now(UTC),
            retrieved_at=observed,
            validation_status="VALID",
            quality_score=score,
            quality_components=components,
            parser_version=PARSER_VERSION,
            validation_version=VALIDATION_VERSION,
            replaces_version_id=previous.id if previous else None,
        )
        self.db.add(version)
        await self.db.flush()
        result["new_versions"] += 1
        audit_service.record(
            self.db,
            event="market.corporate_action_version_created",
            resource="corporate_action_version",
            resource_id=str(version.id),
            actor_user_id=self.actor_user_id,
            metadata={"raw_ingestion_id": str(raw_id)},
        )
        if current:
            current.version_id = version.id
            current.source_id = source_id
            current.raw_ingestion_id = raw_id
            current.validation_status = "VALID"
            current.quality_score = score
            current.quality_components = components
            result["corrected"] += 1
        else:
            self.db.add(
                CorporateAction(
                    instrument_id=row.instrument_id,
                    action_date=d["action_date"],
                    action_type=d["action_type"],
                    version_id=version.id,
                    source_id=source_id,
                    raw_ingestion_id=raw_id,
                    validation_status="VALID",
                    quality_score=score,
                    quality_components=components,
                )
            )
            result["inserted"] += 1

    async def _fx(
        self,
        row: ParsedRow,
        raw_id: UUID,
        source_id: UUID,
        priority: int,
        observed: datetime,
        policy: str,
        result: dict[str, int],
    ) -> None:
        d = row.values
        current = await self.db.get(
            FxRate, (d["base_currency"], d["quote_currency"], d["rate_date"]), with_for_update=True
        )
        existing = await self.db.scalar(
            select(FxRateVersion.id).where(
                FxRateVersion.raw_ingestion_id == raw_id, FxRateVersion.row_number == row.line
            )
        )
        if existing:
            result["unchanged"] += 1
            return
        previous = await self.db.get(FxRateVersion, current.version_id) if current else None
        same = previous is not None and previous.rate == d["rate"]
        if same and previous is not None and previous.source_id == source_id:
            result["unchanged"] += 1
            return
        crosscheck, pct = (
            discrepancy(previous.rate, cast(Decimal, d["rate"]))
            if previous
            else ("NO_REFERENCE", Decimal(0))
        )
        if crosscheck in {"REVIEW", "SEVERE"} and policy == "REJECT":
            raise AppError(
                409,
                "FX_CONFLICT_REVIEW",
                f"Row {row.line}: FX discrepancy {pct:.4f}% requires explicit resolution",
            )
        prior_source = await self.db.get(DataSource, previous.source_id) if previous else None
        lower_priority = (
            previous is not None and prior_source is not None and prior_source.priority < priority
        )
        resolution = (
            "DUPLICATE"
            if same
            else "KEPT_EXISTING"
            if policy == "KEEP_EXISTING" and crosscheck in {"REVIEW", "SEVERE"}
            else "LOWER_PRIORITY"
            if lower_priority and policy != "ACCEPT_NEW"
            else "MANUAL_OVERRIDE"
            if crosscheck in {"REVIEW", "SEVERE"}
            else "ACCEPTED"
        )
        source = await self.db.get(DataSource, source_id)
        assert source is not None
        score, _label, components = quality_score(
            trust=source.trust_level,
            complete_ohlc=True,
            observed_at=observed,
            trading_date=cast(date, d["rate_date"]),
            crosscheck=crosscheck,
            action_checked=True,
        )
        version = FxRateVersion(
            **d,
            source_id=source_id,
            raw_ingestion_id=raw_id,
            row_number=row.line,
            observed_at=observed,
            known_at=datetime.now(UTC),
            retrieved_at=observed,
            validation_status="WARNING"
            if crosscheck in {"NOTICE", "REVIEW", "SEVERE"}
            else "VALID",
            quality_score=score,
            quality_components=components,
            parser_version=PARSER_VERSION,
            validation_version=VALIDATION_VERSION,
            replaces_version_id=previous.id
            if previous and resolution in {"ACCEPTED", "MANUAL_OVERRIDE"}
            else None,
            resolution=resolution,
        )
        self.db.add(version)
        await self.db.flush()
        result["new_versions"] += 1
        if version.validation_status == "WARNING":
            result["warning_rows"] += 1
        audit_service.record(
            self.db,
            event="fx.version_created",
            resource="fx_rate_version",
            resource_id=str(version.id),
            actor_user_id=self.actor_user_id,
            metadata={"resolution": resolution, "raw_ingestion_id": str(raw_id)},
        )
        if resolution not in {"ACCEPTED", "MANUAL_OVERRIDE"}:
            result["observed_only"] += 1
        elif current:
            current.version_id = version.id
            current.rate = cast(Decimal, d["rate"])
            current.source_id = source_id
            current.raw_ingestion_id = raw_id
            current.validation_status = version.validation_status
            current.quality_score = score
            current.quality_components = components
            result["corrected"] += 1
        else:
            self.db.add(
                FxRate(
                    base_currency=d["base_currency"],
                    quote_currency=d["quote_currency"],
                    rate_date=d["rate_date"],
                    version_id=version.id,
                    rate=d["rate"],
                    source_id=source_id,
                    raw_ingestion_id=raw_id,
                    validation_status=version.validation_status,
                    quality_score=score,
                    quality_components=components,
                )
            )
            result["inserted"] += 1
