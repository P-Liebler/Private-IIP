from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import User
from app.repositories.core import find_user_by_id
from app.services.audit import audit_service
from app.services.auth import commit_security_change


class UserSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID) -> User:
        user = await find_user_by_id(self.db, user_id)
        if user is None or not user.is_active:
            raise AppError(401, "UNAUTHENTICATED", "Authentication required")
        return user

    async def update(
        self,
        user_id: UUID,
        changes: dict[str, str],
        *,
        ip_address: str,
    ) -> User:
        user = await find_user_by_id(self.db, user_id, for_update=True)
        if user is None or not user.is_active:
            raise AppError(401, "UNAUTHENTICATED", "Authentication required")
        changed: dict[str, str | int | bool | None] = {}
        for field in ("timezone", "base_currency"):
            value = changes.get(field)
            if value is not None and getattr(user, field) != value:
                setattr(user, field, value)
                changed[field] = value
        if changed:
            audit_service.record(
                self.db,
                event="settings.changed",
                resource="user_settings",
                actor_user_id=user.id,
                resource_id=str(user.id),
                metadata={"changed_fields": ",".join(sorted(changed))},
                ip_address=ip_address,
            )
            await commit_security_change(self.db)
        return user
