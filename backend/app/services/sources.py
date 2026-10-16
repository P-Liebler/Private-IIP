from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataSource, SourceReviewEvidence
from app.services.audit import audit_service


class SourceGate:
    @staticmethod
    def require_enabled(source: DataSource, use: str) -> None:
        now = datetime.now(UTC)
        if source.gate_status != "APPROVED" or not source.enabled:
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source is not approved for this use")
        if source.checked_at is None or source.checked_at > now:
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source review is missing or invalid")
        if source.type != "MANUAL" and (
            not source.terms_url
            or not source.scope
            or not source.decision_by
            or source.next_review_at is None
            or source.next_review_at <= now
        ):
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source review is missing or expired")
        if use not in source.allowed_uses:
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source use is not approved")


class SourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self) -> Sequence[DataSource]:
        return [*(await self.db.scalars(select(DataSource).order_by(DataSource.priority))).all()]

    async def get(self, slug: str, *, lock: bool = False) -> DataSource:
        statement = select(DataSource).where(DataSource.slug == slug.upper())
        if lock:
            statement = statement.with_for_update()
        source = (await self.db.scalars(statement)).one_or_none()
        if source is None:
            raise AppError(404, "SOURCE_NOT_FOUND", "Source not found")
        return source

    async def review(
        self,
        slug: str,
        *,
        status: str,
        terms_url: str | None,
        scope: str,
        allowed_uses: Sequence[str],
        decision_note: str,
        decision_by: str,
        next_review_at: datetime | None,
        rate_limit_per_minute: int | None = None,
        actor_user_id: UUID | None = None,
    ) -> DataSource:
        if status not in {"APPROVED", "BLOCKED", "UNKNOWN"}:
            raise ValueError("Invalid gate status")
        if not decision_by.strip() or not decision_note.strip():
            raise ValueError("Reviewer and decision note are required")
        source = await self.get(slug, lock=True)
        if source.type != "MANUAL" and status == "APPROVED":
            if not terms_url or not terms_url.startswith("https://") or not scope.strip():
                raise ValueError("External approval requires HTTPS terms URL and scope")
            if next_review_at is None or next_review_at <= datetime.now(UTC):
                raise ValueError("External approval requires a future review date")
            if not allowed_uses:
                raise ValueError("External approval requires allowed uses")
            if rate_limit_per_minute is None or rate_limit_per_minute < 1:
                raise ValueError("External approval requires a positive rate limit")
        source.gate_status = status
        source.enabled = False  # A new decision never silently enables a provider.
        source.terms_url = terms_url
        source.checked_at = datetime.now(UTC)
        source.scope = scope
        source.allowed_uses = sorted(set(allowed_uses)) if status == "APPROVED" else []
        source.decision_note = decision_note
        source.decision_by = decision_by
        source.next_review_at = next_review_at
        source.rate_limit_per_minute = rate_limit_per_minute
        self.db.add(
            SourceReviewEvidence(
                source_id=source.id,
                decision={
                    "status": status,
                    "terms_url": terms_url,
                    "scope": scope,
                    "allowed_uses": list(allowed_uses),
                    "decision_note": decision_note,
                    "decision_by": decision_by,
                    "checked_at": source.checked_at.isoformat(),
                    "next_review_at": next_review_at.isoformat() if next_review_at else None,
                    "rate_limit_per_minute": rate_limit_per_minute,
                },
            )
        )
        audit_service.record(
            self.db,
            event="source.reviewed",
            actor_user_id=actor_user_id,
            resource="data_source",
            resource_id=str(source.id),
            metadata={"slug": source.slug, "gate_status": status, "decision_by": decision_by},
        )
        await self.db.commit()
        return source

    async def enable(self, slug: str, *, actor_user_id: UUID | None = None) -> DataSource:
        source = await self.get(slug, lock=True)
        # Check the approval in the same transaction as enabling.
        source.enabled = True
        try:
            SourceGate.require_enabled(source, next(iter(source.allowed_uses), ""))
        except AppError:
            source.enabled = False
            raise
        audit_service.record(
            self.db,
            event="source.enabled",
            actor_user_id=actor_user_id,
            resource="data_source",
            resource_id=str(source.id),
            metadata={"slug": source.slug},
        )
        await self.db.commit()
        return source

    async def disable(self, slug: str, *, actor_user_id: UUID | None = None) -> DataSource:
        source = await self.get(slug, lock=True)
        source.enabled = False
        audit_service.record(
            self.db,
            event="source.disabled",
            actor_user_id=actor_user_id,
            resource="data_source",
            resource_id=str(source.id),
            metadata={"slug": source.slug},
        )
        await self.db.commit()
        return source
