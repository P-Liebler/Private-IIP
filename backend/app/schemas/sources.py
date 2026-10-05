from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models import DataSource


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    type: str
    trust_level: str
    priority: int
    enabled: bool
    gate_status: str
    terms_url: str | None
    checked_at: datetime | None
    scope: str | None
    allowed_uses: list[str]
    next_review_at: datetime | None
    rate_limit_per_minute: int | None
    last_success: datetime | None
    last_failure: datetime | None

    @classmethod
    def from_record(cls, source: DataSource) -> DataSourceResponse:
        return cls(
            id=source.id,
            name=source.name,
            slug=source.slug,
            type=source.type,
            trust_level=source.trust_level,
            priority=source.priority,
            enabled=source.enabled,
            gate_status=source.gate_status,
            terms_url=source.terms_url,
            checked_at=source.checked_at,
            scope=source.scope,
            allowed_uses=source.allowed_uses,
            next_review_at=source.next_review_at,
            rate_limit_per_minute=source.rate_limit_per_minute,
            last_success=source.last_success,
            last_failure=source.last_failure,
        )
