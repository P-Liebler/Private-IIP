"""Durable bounded collection. Celery is a wakeup; PostgreSQL owns progress."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.models import CollectorJob, DataSource, Instrument, RawIngestion, User
from app.schemas.data_operations import CollectionInput
from app.services.audit import audit_service
from app.services.fundamentals import digest
from app.services.pit_features import json_value
from app.services.sources import SourceGate, SourceService
from app.services.work_limits import work_slot

KINDS = {
    "ECB_FX": ("ECB", "fx_rates"),
    "SNB_MACRO": ("SNB", "macro"),
    "SEC": ("SEC_EDGAR", "fundamentals"),
    "OPENFIGI": ("OPENFIGI", "mapping"),
    "MANUAL_PRICES": ("MANUAL_CSV", "manual_upload"),
    "ALPHA_PRICES": ("ALPHAVANTAGE", "prices"),
}


def chunks(request: CollectionInput) -> list[tuple[date, date]]:
    if request.kind in {"SEC", "OPENFIGI", "MANUAL_PRICES", "COVERAGE", "ALPHA_PRICES"}:
        return [(request.start, request.end)]
    size = 32 if request.kind == "ECB_FX" else 365
    result = []
    current = request.start
    while current <= request.end:
        end = min(request.end, current + timedelta(days=size - 1))
        result.append((current, end))
        current = end + timedelta(days=1)
    return result


class BackfillJobService:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db, self.user = db, user
        self.user_id = user.id

    async def preview(self, request: CollectionInput) -> dict[str, Any]:
        await self.db.refresh(self.user)
        if not self.user.is_active:
            raise AppError(403, "DATA_OPERATOR_REQUIRED", "Active data operator required")
        require_data_operator(self.user)
        if request.end > datetime.now(UTC).date():
            raise AppError(422, "DATE_RANGE_INVALID", "Future collection prohibited")
        source = await SourceService(self.db).get(request.source_slug)
        if request.kind != "COVERAGE":
            slug, use = KINDS[request.kind]
            if source.slug != slug:
                raise AppError(422, "COLLECTOR_CONTRACT_INVALID", "Provider and data type mismatch")
            SourceGate.require_enabled(source, use)
        for iid in request.instrument_ids:
            if await self.db.get(Instrument, iid) is None:
                raise AppError(404, "INSTRUMENT_NOT_FOUND", "Select stable existing instruments")
        actual_instruments = [str(i) for i in request.instrument_ids]
        if request.kind == "MANUAL_PRICES":
            raw = await self.db.get(RawIngestion, request.raw_ingestion_id)
            if (
                not raw
                or raw.source_id != source.id
                or raw.resource_type != "manual_prices_csv"
                or raw.request_metadata.get("user_id") != str(self.user.id)
            ):
                raise AppError(404, "RAW_NOT_FOUND", "Owned previewed price upload required")
            from app.services.market_import import MarketImportService
            from app.services.raw_ingestion import RawIngestionService

            data = await RawIngestionService(self.db).get_verified(raw.id)
            rows, errors, _ = await MarketImportService(self.db)._parse(
                "prices", data, request.mapping
            )
            if errors or any(
                r.errors
                or not r.instrument_id
                or not request.start <= cast(date, r.values["trading_date"]) <= request.end
                for r in rows
            ):
                raise AppError(
                    422,
                    "BACKFILL_PREVIEW_INVALID",
                    "Review mappings, identities and requested range",
                )
            instruments = {r.instrument_id for r in rows}
            actual_instruments = sorted(str(i) for i in instruments if i is not None)
            if (
                not rows
                or len(instruments) > 30
                or (request.instrument_ids and not instruments <= set(request.instrument_ids))
            ):
                raise AppError(
                    422, "BACKFILL_SCOPE_INVALID", "At most 30 explicitly scoped instruments"
                )
        count = len(chunks(request))
        return {
            "status": "READY",
            "source_id": str(source.id),
            "chunks": count,
            "maximum_requests": 0
            if request.kind in {"MANUAL_PRICES", "COVERAGE"}
            else count * (6 if request.kind == "SEC" else 3),
            "instruments": len(actual_instruments),
            "instrument_ids": actual_instruments,
            "configuration_hash": digest(request.model_dump(mode="json")),
            "range": [request.start.isoformat(), request.end.isoformat()],
            "limitations": [
                "Backfill is not locally archived historical knowledge",
                "No promotion or action coverage approval",
            ],
        }

    async def start(self, request: CollectionInput) -> CollectorJob:
        preview = await self.preview(request)
        async with work_slot(917000):
            pending = await self.db.scalar(
                select(func.count())
                .select_from(CollectorJob)
                .where(CollectorJob.status.in_(["QUEUED", "RUNNING"]))
            )
            if pending and pending >= 4:
                raise AppError(429, "COLLECTOR_QUEUE_FULL", "At most four pending collector jobs")
            configuration = request.model_dump(mode="json")
            if request.kind == "MANUAL_PRICES" and not request.instrument_ids:
                configuration["instrument_ids"] = preview["instrument_ids"]
            existing = (
                await self.db.scalars(
                    select(CollectorJob).where(
                        CollectorJob.configuration == configuration,
                        CollectorJob.status.in_(["QUEUED", "RUNNING"]),
                    )
                )
            ).first()
            if existing:
                if existing.user_id != self.user.id:
                    raise AppError(
                        409, "COLLECTION_ALREADY_RUNNING", "Equivalent collection already pending"
                    )
                return existing
            job = CollectorJob(
                user_id=self.user.id,
                source_id=UUID(preview["source_id"]),
                status="QUEUED",
                configuration=configuration,
                progress=0,
                results=[],
                cancel_requested=False,
            )
            self.db.add(job)
            await self.db.flush()
            audit_service.record(
                self.db,
                event="collector.queued",
                resource="collector_job",
                resource_id=str(job.id),
                actor_user_id=self.user_id,
                metadata={"kind": request.kind, "source_slug": request.source_slug},
            )
            await self.db.commit()
            return job

    async def owned(self, identifier: UUID) -> CollectorJob:
        await self.db.refresh(self.user)
        require_data_operator(self.user)
        row = await self.db.get(CollectorJob, identifier)
        if row is None or row.user_id != self.user.id:
            raise AppError(404, "COLLECTOR_JOB_NOT_FOUND", "Private collector job missing")
        return row

    async def control(self, identifier: UUID, action: str) -> CollectorJob:
        row = await self.owned(identifier)
        if action == "cancel":
            row.cancel_requested = True
            if row.status != "RUNNING":
                row.status = "CANCELLED"
        elif action == "resume" and row.status in {"FAILED", "PARTIAL", "CANCELLED", "SKIPPED"}:
            await self.preview(CollectionInput.model_validate(row.configuration))
            row.status, row.cancel_requested, row.last_error_code = "QUEUED", False, None
        else:
            raise AppError(409, "JOB_STATE_INVALID", "Operation unavailable in this job state")
        audit_service.record(
            self.db,
            event="collector." + action,
            resource="collector_job",
            resource_id=str(identifier),
            actor_user_id=self.user_id,
            metadata={"status": row.status},
        )
        await self.db.commit()
        return row

    async def execute(self, identifier: UUID) -> CollectorJob:
        async with work_slot(917001):
            job = await self.owned(identifier)
            if job.status not in {"QUEUED", "RUNNING"}:
                return job
            request = CollectionInput.model_validate(job.configuration)
            try:
                await self.preview(request)  # Recheck operator and rights after queue/restart.
                job.status, job.started_at = "RUNNING", datetime.now(UTC)
                await self.db.commit()
                for index, (start, end) in enumerate(chunks(request)):
                    if index < job.progress:
                        continue
                    await self.db.refresh(job)
                    if job.cancel_requested:
                        job.status = "CANCELLED"
                        break
                    await self.preview(request)
                    async with asyncio.timeout(150):
                        result = await self.collect(request, start, end)
                    result["requested_range"] = [start.isoformat(), end.isoformat()]
                    # Raw/canonical commits precede the replayable checkpoint.
                    job.results = [*job.results, json_value(result)]
                    job.progress = index + 1
                    await self.db.commit()
                else:
                    job.status = (
                        "PARTIAL"
                        if any(
                            r.get("status") == "PARTIAL" or r.get("quarantined", 0)
                            for r in job.results
                        )
                        else "SUCCESS"
                    )
                job.completed_at = datetime.now(UTC)
            except Exception as error:
                await self.db.rollback()
                recovered = await self.db.get(CollectorJob, identifier)
                if recovered is None or recovered.user_id != self.user_id:
                    raise AppError(
                        404, "COLLECTOR_JOB_NOT_FOUND", "Collector job missing"
                    ) from None
                job = recovered
                job.last_error_code = (
                    error.code if isinstance(error, AppError) else "COLLECTOR_FAILED"
                )
                job.status = (
                    "SKIPPED"
                    if job.last_error_code in {"SOURCE_NOT_APPROVED", "DATA_OPERATOR_REQUIRED"}
                    else "PARTIAL"
                    if job.progress
                    else "FAILED"
                )
                job.completed_at = datetime.now(UTC)
                source = await self.db.get(DataSource, job.source_id)
                if source and job.last_error_code not in {
                    "SOURCE_NOT_APPROVED",
                    "DATA_OPERATOR_REQUIRED",
                }:
                    source.last_failure = job.completed_at
                    source.failure_count += 1
            audit_service.record(
                self.db,
                event="collector.finished",
                resource="collector_job",
                resource_id=str(identifier),
                actor_user_id=self.user_id,
                metadata={"status": job.status, "error_code": job.last_error_code},
            )
            await self.db.commit()
            return job

    async def collect(self, request: CollectionInput, start: date, end: date) -> dict[str, Any]:
        from app.providers.alpha_vantage import AlphaVantageCollector
        from app.providers.ecb_fx import EcbFxCollector
        from app.providers.openfigi import OpenFigiProvider
        from app.providers.sec import SecCollector
        from app.providers.snb_fx import SnbFxCollector
        from app.services.data_coverage import DataCoverageService
        from app.services.market_import import MarketImportService

        if request.kind == "ALPHA_PRICES":
            return await AlphaVantageCollector(self.db).collect(
                request.instrument_ids[0], start, end
            )
        if request.kind == "ECB_FX":
            return await EcbFxCollector(self.db).collect(start, end)
        if request.kind == "SNB_MACRO":
            return await SnbFxCollector(self.db).collect(start, end, request.series)
        if request.kind == "SEC":
            return await SecCollector(self.db).collect(request.instrument_ids[0], request.cik or "")
        if request.kind == "OPENFIGI":
            instrument = await self.db.get(Instrument, request.instrument_ids[0])
            assert instrument
            kind, value = (
                ("ISIN", instrument.isin) if instrument.isin else ("FIGI", instrument.figi)
            )
            if not value:
                raise AppError(422, "IDENTITY_REVIEW_REQUIRED", "Reviewed ISIN or FIGI required")
            result = await OpenFigiProvider(self.db).map_identifier(
                kind=kind,
                value=value,
                mic=instrument.mic,
                currency=instrument.currency,
                include_unlisted=request.include_unlisted,
            )
            return {
                "status": result.status,
                "raw_ingestion_id": str(result.raw_ingestion_id),
                "candidates": len(result.candidates),
                "accepted": False,
            }
        if request.kind == "MANUAL_PRICES":
            assert request.raw_ingestion_id
            return await MarketImportService(self.db).commit(
                "prices", request.raw_ingestion_id, request.mapping, actor_user_id=self.user.id
            )
        coverage_results = []
        for iid in request.instrument_ids:
            coverage_results.append(
                await DataCoverageService(self.db, self.user.id).inspect(iid, start, end, save=True)
            )
        return {"status": "SUCCESS", "coverage": coverage_results}
