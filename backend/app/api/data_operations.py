import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.assistant.documents import require_data_operator
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.models import CollectorJob, SourceReviewEvidence
from app.schemas.data_operations import CollectionInput, SourceReviewInput
from app.services.action_coverage import CoverageReviewInput, review_coverage
from app.services.auth import AuthContext
from app.services.backfill_jobs import BackfillJobService
from app.services.data_coverage import DataCoverageService
from app.services.ir_reports import IRReportReviewService, ReportReviewInput
from app.services.rate_limit import rate_limiter
from app.services.sources import SourceService

router = APIRouter(prefix="/api/v1/data-operations", tags=["data operations"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.post("/action-coverage/reviews", status_code=201)
async def action_review(request: CoverageReviewInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await review_coverage(db, context.user, request))


@router.get("")
async def overview(db: DB, context: Auth) -> dict[str, Any]:
    rows = (
        await db.scalars(
            select(CollectorJob)
            .where(CollectorJob.user_id == context.user.id)
            .order_by(CollectorJob.created_at.desc())
            .limit(50)
        )
    ).all()
    return {
        "is_operator": context.user.username in get_settings().data_operator_usernames,
        "scheduling_enabled": get_settings().data_collection_enabled,
        "daily_request_limit": get_settings().max_daily_provider_requests,
        "jobs": [view(row) for row in rows],
        "limits": {"instruments": 30, "days": 1826, "pending_jobs": 4},
        "source_approval": "PARTIAL",
        "forecast_validation": "NOT_VALIDATED",
        "recommendations": "GATED",
        "production": "NOT_RELEASED",
    }


@router.post("/preview")
async def preview(request: CollectionInput, db: DB, context: Auth) -> dict[str, Any]:
    return await BackfillJobService(db, context.user).preview(request)


@router.post("/jobs", status_code=201)
async def start(request: CollectionInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await BackfillJobService(db, context.user).start(request))


@router.get("/jobs/{identifier}")
async def job(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await BackfillJobService(db, context.user).owned(identifier))


@router.post("/jobs/{identifier}/{action}")
async def control(
    identifier: UUID, action: Literal["cancel", "resume"], db: DB, context: Auth
) -> dict[str, Any]:
    return view(await BackfillJobService(db, context.user).control(identifier, action))


@router.post("/sources/{slug}/review")
async def review(slug: str, request: SourceReviewInput, db: DB, context: Auth) -> dict[str, Any]:
    require_data_operator(context.user)
    try:
        row = await SourceService(db).review(
            slug,
            **request.model_dump(),
            decision_by=context.user.username,
            actor_user_id=context.user.id,
        )
    except ValueError:
        raise AppError(
            422, "SOURCE_REVIEW_INVALID", "Complete rights evidence and review date required"
        ) from None
    return view(row)


@router.post("/sources/{slug}/{action}")
async def source_action(
    slug: str, action: Literal["enable", "disable"], db: DB, context: Auth
) -> dict[str, Any]:
    require_data_operator(context.user)
    service = SourceService(db)
    return view(
        await (
            service.enable(slug, actor_user_id=context.user.id)
            if action == "enable"
            else service.disable(slug, actor_user_id=context.user.id)
        )
    )


@router.get("/sources/{slug}/reviews")
async def reviews(slug: str, db: DB, context: Auth) -> list[dict[str, Any]]:
    require_data_operator(context.user)
    source = await SourceService(db).get(slug)
    rows = (
        await db.scalars(
            select(SourceReviewEvidence)
            .where(SourceReviewEvidence.source_id == source.id)
            .order_by(SourceReviewEvidence.created_at.desc())
            .limit(100)
        )
    ).all()
    return [view(r) for r in rows]


@router.get("/coverage/{instrument_id}")
async def coverage(
    instrument_id: UUID,
    db: DB,
    context: Auth,
    start: date | None = None,
    end: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    await rate_limiter.check_work("coverage", str(context.user.id), 20)
    end = end or datetime.now(UTC).date()
    try:
        async with asyncio.timeout(90):
            return await DataCoverageService(db, context.user.id).inspect(
                instrument_id, start or end - timedelta(days=45), end, as_of
            )
    except TimeoutError:
        raise AppError(503, "COVERAGE_TIMEOUT", "Select a smaller coverage interval") from None


@router.post("/ir-reports/{source_slug}/{instrument_id}/upload", status_code=201)
async def upload_report(
    source_slug: str, instrument_id: UUID, request: Request, db: DB, context: Auth
) -> dict[str, Any]:
    require_data_operator(context.user)
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > 5_000_000:
            raise AppError(413, "REPORT_SIZE_LIMIT", "Maximum 5 MB")
        data.extend(part)
    return view(
        await IRReportReviewService(db, context.user).upload(
            source_slug, instrument_id, bytes(data)
        )
    )


@router.get("/ir-reports/{raw_id}/preview")
async def preview_report(raw_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return await IRReportReviewService(db, context.user).preview(raw_id)


@router.post("/ir-reports/{raw_id}/commit")
async def commit_report(
    raw_id: UUID, request: ReportReviewInput, db: DB, context: Auth
) -> dict[str, int]:
    return await IRReportReviewService(db, context.user).commit(raw_id, request)
