from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


class AuditService:
    def record(
        self,
        db: AsyncSession,
        *,
        event: str,
        resource: str,
        actor_user_id: UUID | None = None,
        resource_id: str | None = None,
        metadata: dict[str, str | int | bool | None] | None = None,
        ip_address: str | None = None,
    ) -> None:
        db.add(
            AuditEvent(
                event=event,
                resource=resource,
                actor_user_id=actor_user_id,
                resource_id=resource_id,
                metadata_json=metadata or {},
                ip_address=ip_address,
            )
        )


audit_service = AuditService()
