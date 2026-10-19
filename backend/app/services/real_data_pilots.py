from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import require_data_operator
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import CollectorJob, DataSource, User, ValidationRecord
from app.schemas.validation import PilotInput, RawEvidenceInput
from app.services.backfill_jobs import BackfillJobService
from app.services.fundamentals import digest
from app.services.raw_ingestion import RawIngestionService
from app.services.real_data_readiness import RealDataReadinessService
from app.services.validation_records import ValidationRecords
from app.services.work_limits import work_slot


class RealDataPilotService:
    def __init__(self, db: AsyncSession, user: User):
        self.db, self.user = db, user
        self.records = ValidationRecords(db, user.id)

    async def preview(self, request: PilotInput) -> ValidationRecord:
        require_data_operator(self.user)
        report = await RealDataReadinessService(self.db, self.user.id).report(request.readiness)
        previews, blockers = [], []
        for collection in request.collections:
            try:
                preview = await BackfillJobService(self.db, self.user).preview(collection)
                if collection.kind != "MANUAL_PRICES":
                    settings = get_settings()
                    if settings.app_env == "test":
                        raise AppError(
                            403,
                            "LIVE_SMOKE_ENV_BLOCKED",
                            "External pilot requires operational environment",
                        )
                    if collection.kind == "ALPHA_PRICES" and not settings.alpha_vantage_api_key:
                        raise AppError(409, "SOURCE_KEY_REQUIRED", "Personal key required")
                    if collection.kind == "SEC" and (
                        not settings.sec_enabled
                        or not settings.sec_contact_email
                        or not settings.sec_user_agent
                    ):
                        raise AppError(
                            409, "SEC_CONFIGURATION_REQUIRED", "SEC configuration required"
                        )
                previews.append(preview)
            except AppError as error:
                blockers.append({"source_slug": collection.source_slug, "code": error.code})
        return await self.records.append(
            "PILOT_PREVIEW",
            request.model_dump(mode="json"),
            {
                "status": "LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED"
                if any(b["code"] == "SOURCE_NOT_APPROVED" for b in blockers)
                else "BLOCKED"
                if blockers
                else "PREVIEW_READY",
                "blockers": blockers,
                "previews": previews,
                "readiness": report,
                "real_data_acceptance": "NOT_ESTABLISHED",
            },
        )

    async def start(self, identifier: UUID) -> ValidationRecord:
        require_data_operator(self.user)
        pilot = await self.records.owned(identifier, "PILOT_PREVIEW")
        request = PilotInput.model_validate(pilot.request)
        async with work_slot(917010):
            jobs, blockers = [], []
            links = {
                r.dedup_key: r
                for r in (
                    await self.db.scalars(
                        select(ValidationRecord).where(
                            ValidationRecord.user_id == self.user.id,
                            ValidationRecord.kind == "PILOT_JOB",
                            ValidationRecord.parent_id == pilot.id,
                        )
                    )
                ).all()
            }
            # Revalidate all requests before creating any new collector job.
            refreshed = await self.preview(request)
            if refreshed.result["status"] != "PREVIEW_READY":
                return await self.records.append(
                    "PILOT_STARTED",
                    {},
                    {
                        "status": refreshed.result["status"],
                        "blockers": refreshed.result["blockers"],
                        "job_ids": [],
                    },
                    parent_id=pilot.id,
                )
            for collection in request.collections:
                key = digest(
                    {"pilot": str(pilot.id), "request": collection.model_dump(mode="json")}
                )
                if key in links:
                    jobs.append(links[key].result["job_id"])
                    continue
                try:
                    job = await BackfillJobService(self.db, self.user).start(collection)
                    jobs.append(str(job.id))
                    await self.records.append(
                        "PILOT_JOB",
                        collection.model_dump(mode="json"),
                        {"job_id": str(job.id)},
                        parent_id=pilot.id,
                        dedup_key=key,
                    )
                except AppError as error:
                    blockers.append(error.code)
                    break
            return await self.records.append(
                "PILOT_STARTED",
                {},
                {
                    "status": "PARTIAL_QUEUE" if blockers else "QUEUED",
                    "job_ids": jobs,
                    "blockers": blockers,
                    "resume": "Retry start after jobs finish; existing links are retained",
                },
                parent_id=pilot.id,
            )

    async def assess(self, identifier: UUID) -> ValidationRecord:
        pilot = await self.records.owned(identifier, "PILOT_PREVIEW")
        jobs = []
        for link in (
            await self.db.scalars(
                select(ValidationRecord).where(
                    ValidationRecord.user_id == self.user.id,
                    ValidationRecord.kind == "PILOT_JOB",
                    ValidationRecord.parent_id == pilot.id,
                )
            )
        ).all():
            if link.parent_id == pilot.id:
                job = await self.db.get(CollectorJob, UUID(link.result["job_id"]))
                if not job or job.user_id != self.user.id:
                    raise AppError(409, "PILOT_JOB_MISSING", "Pinned job unavailable")
                jobs.append(
                    {
                        "id": str(job.id),
                        "status": job.status,
                        "results": job.results,
                        "error_code": job.last_error_code,
                    }
                )
        report = await RealDataReadinessService(self.db, self.user.id).report(
            PilotInput.model_validate(pilot.request).readiness
        )
        return await self.records.append(
            "PILOT_ACCEPTANCE",
            {},
            {
                "jobs": jobs,
                "readiness": report,
                "status": "PR2A REAL_DATA_READY"
                if report["readiness_status"] == "REAL_DATA_READY"
                and len(jobs) == len(pilot.request["collections"])
                and all(j["status"] == "SUCCESS" for j in jobs)
                else "PR2A BLOCKED_BY_SOURCE_APPROVAL"
                if "SOURCE_APPROVAL_REQUIRED" in report["blocking_reasons"]
                else "PR2A PARTIAL_REAL_DATA",
            },
            parent_id=pilot.id,
        )

    async def evidence(self, request: RawEvidenceInput) -> ValidationRecord:
        require_data_operator(self.user)
        originals = []
        for identifier in request.raw_ids:
            raw = await RawIngestionService(self.db).get(identifier)
            if raw.request_metadata.get("user_id") not in (None, str(self.user.id)):
                raise AppError(404, "RAW_NOT_FOUND", "Private original unavailable")
            source = await self.db.get(DataSource, raw.source_id)
            assert source
            body = await RawIngestionService(self.db).get_verified(identifier)
            if not body or (raw.http_status is not None and not 200 <= raw.http_status < 300):
                raise AppError(
                    422, "ORIGINAL_NOT_USABLE", "A complete successful original is required"
                )
            synthetic = (
                source.slug.startswith("TEST_")
                or "synthetic" in str(raw.request_metadata.get("filename", "")).lower()
            )
            if request.classification.startswith("REAL_") and synthetic:
                raise AppError(
                    422,
                    "SYNTHETIC_EVIDENCE_FORBIDDEN",
                    "Test originals cannot become real evidence",
                )
            if request.classification == "REAL_MANUAL" and (
                source.type != "MANUAL" or raw.requested_at is not None
            ):
                raise AppError(422, "ORIGIN_CLASSIFICATION_MISMATCH", "Manual original required")
            if request.classification == "REAL_PROVIDER" and (
                source.type == "MANUAL" or raw.http_status != 200
            ):
                raise AppError(
                    422, "ORIGIN_CLASSIFICATION_MISMATCH", "Archived provider response required"
                )
            originals.append(
                {
                    "raw_id": str(raw.id),
                    "sha256": raw.sha256,
                    "source_id": str(source.id),
                    "received_at": raw.received_at.isoformat(),
                }
            )
        return await self.records.append(
            "RAW_EVIDENCE",
            request.model_dump(mode="json"),
            {
                "originals": originals,
                "reviewed_at": datetime.now(UTC).isoformat(),
                "reviewer_id": str(self.user.id),
                "public_availability": "UNCHANGED_REQUIRES_P6_EVIDENCE",
                "rights": "Does not change SourceGate or document rights",
            },
        )
