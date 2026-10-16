"""Operator evidence for exact action types, instrument and interval only."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.models import ActionCoverageReview, CorporateAction, CorporateActionVersion, User
from app.schemas.pit import StrictModel
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class CoverageReviewInput(StrictModel):
    instrument_id: UUID
    start: date
    end: date
    source_slug: str = Field(max_length=60)
    raw_ingestion_id: UUID
    action_types: list[
        Literal["SPLIT", "DIVIDEND", "REVERSE_SPLIT", "TICKER_CHANGE", "DELISTING"]
    ] = Field(min_length=1, max_length=5)
    action_version_ids: list[UUID] = Field(max_length=1000)
    history_reference: str = Field(min_length=20, max_length=1000)
    cross_check: str = Field(min_length=20, max_length=1000)
    completeness_method: str = Field(min_length=20, max_length=1000)
    rationale: str = Field(min_length=40, max_length=2000)


async def review_coverage(
    db: AsyncSession, user: User, request: CoverageReviewInput
) -> ActionCoverageReview:
    require_data_operator(user)
    if request.end < request.start or (request.end - request.start).days > 1826:
        raise AppError(422, "COVERAGE_RANGE_INVALID", "Ordered bounded interval required")
    source = await SourceService(db).get(request.source_slug)
    SourceGate.require_enabled(source, "action_coverage")
    raw_service = RawIngestionService(db)
    raw = await raw_service.get(request.raw_ingestion_id)
    if raw.source_id != source.id:
        raise AppError(422, "EVIDENCE_RAW_MISMATCH", "Exact reviewed source original required")
    body = await raw_service.get_verified(raw.id)
    if not body or (raw.http_status is not None and not 200 <= raw.http_status < 300):
        raise AppError(422, "EVIDENCE_RAW_INVALID", "Nonempty successful source evidence required")
    current = (
        await db.scalars(
            select(CorporateActionVersion)
            .join(CorporateAction, CorporateAction.version_id == CorporateActionVersion.id)
            .where(
                CorporateActionVersion.instrument_id == request.instrument_id,
                CorporateActionVersion.action_date.between(request.start, request.end),
                CorporateActionVersion.action_type.in_(request.action_types),
            )
        )
    ).all()
    if {r.id for r in current} != set(request.action_version_ids) or any(
        r.validation_status == "REJECTED" for r in current
    ):
        raise AppError(
            409,
            "COVERAGE_VERSIONS_CHANGED",
            "Review all current versions of the selected event types",
        )
    row = ActionCoverageReview(
        instrument_id=request.instrument_id,
        start_date=request.start,
        end_date=request.end,
        source_id=source.id,
        raw_ingestion_id=raw.id,
        reviewer_id=user.id,
        action_types=sorted(set(request.action_types)),
        action_version_ids=sorted(str(i) for i in request.action_version_ids),
        rationale=request.rationale,
        coverage_evidence={
            "history_reference": request.history_reference,
            "cross_check": request.cross_check,
            "completeness_method": request.completeness_method,
        },
    )
    db.add(row)
    await db.commit()
    return row
