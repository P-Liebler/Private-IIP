from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    ActionCoverageReview,
    AnalystEstimate,
    AvailabilityReview,
    CorporateActionVersion,
    FundamentalFact,
    FxRateVersion,
    MacroObservation,
    NewsArticle,
    NewsMappingVersion,
    PriceDailyVersion,
    UniverseDefinition,
    UniverseMembershipVersion,
)
from app.services.raw_ingestion import RawIngestionService

ENTITIES: dict[str, Any] = {
    "coverage": ActionCoverageReview,
    "evidence": AvailabilityReview,
    "mapping": NewsMappingVersion,
    "macro": MacroObservation,
    "price": PriceDailyVersion,
    "fact": FundamentalFact,
    "fx": FxRateVersion,
    "action": CorporateActionVersion,
    "news": NewsArticle,
    "estimate": AnalystEstimate,
    "membership": UniverseMembershipVersion,
    "universe": UniverseDefinition,
}
LEVELS = {
    "VERIFIED_PUBLIC_TIMESTAMP",
    "VERIFIED_SOURCE_DOCUMENT",
    "LOCAL_FIRST_OBSERVATION",
    "USER_ASSERTED",
    "UNVERIFIED",
}


class EvidenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def review(
        self,
        kind: str,
        entity_id: UUID,
        raw_id: UUID,
        reviewer_id: UUID,
        level: str,
        rationale: str,
        evidence: dict[str, Any],
    ) -> AvailabilityReview:
        model = ENTITIES.get(kind)
        if model is None or level not in LEVELS or len(rationale.strip()) < 20:
            raise AppError(
                422, "EVIDENCE_REVIEW_INVALID", "Concrete review and recognized level required"
            )
        entity = await self.db.get(model, entity_id)
        if entity is None:
            raise AppError(404, "EVIDENCE_ENTITY_NOT_FOUND", "Version not found")
        if kind != "universe" and entity.raw_ingestion_id != raw_id:
            raise AppError(422, "EVIDENCE_RAW_MISMATCH", "Review must reference the exact original")
        await RawIngestionService(self.db).get_verified(raw_id)
        if level.startswith("VERIFIED_") and not all(
            evidence.get(k) for k in ("document_reference", "checked_timestamp", "method")
        ):
            raise AppError(
                422,
                "EVIDENCE_REVIEW_INVALID",
                "Document, timestamp and concrete review method required",
            )
        row = AvailabilityReview(
            entity_type=kind,
            entity_id=entity_id,
            raw_ingestion_id=raw_id,
            reviewer_id=reviewer_id,
            level=level,
            rationale=rationale,
            evidence=evidence,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def latest(
        self, kind: str, entity_id: UUID, cutoff: datetime | None = None
    ) -> AvailabilityReview | None:
        query = select(AvailabilityReview).where(
            AvailabilityReview.entity_type == kind, AvailabilityReview.entity_id == entity_id
        )
        if cutoff:
            query = query.where(AvailabilityReview.created_at <= cutoff)
        return (
            await self.db.scalars(
                query.order_by(
                    AvailabilityReview.created_at.desc(), AvailabilityReview.id.desc()
                ).limit(1)
            )
        ).first()
