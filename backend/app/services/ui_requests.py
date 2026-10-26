"""Commit a resource and its retry receipt in the same PostgreSQL transaction."""

import hashlib
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Portfolio, PortfolioAccount, UIRequest
from app.services.fundamentals import digest

T = TypeVar("T", Portfolio, PortfolioAccount)


async def request_checkpoint(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    records = (
        await db.scalars(
            select(UIRequest).where(UIRequest.user_id == user_id).order_by(UIRequest.request_id)
        )
    ).all()
    content = [
        {column.name: getattr(row, column.name) for column in UIRequest.__table__.columns}
        for row in records
    ]
    return {"ui_request_history_hash": digest(content), "ui_request_count": len(records)}


async def create_once(
    db: AsyncSession,
    user_id: UUID,
    key: UUID | None,
    operation: str,
    payload: dict[str, Any],
    model: type[T],
    create: Callable[[], Awaitable[T]],
) -> T:
    if key is None:
        return await create()
    lock = int.from_bytes(hashlib.sha256(user_id.bytes + key.bytes).digest()[:8], signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": lock})
    request_hash = digest({"operation": operation, "payload": payload})
    previous = await db.get(UIRequest, (user_id, key))
    if previous is not None:
        if previous.operation != operation or previous.payload_hash != request_hash:
            raise AppError(
                409, "REQUEST_KEY_CONFLICT", "Retry key already belongs to different inputs"
            )
        resource = await db.get(model, previous.resource_id)
        if resource is None:
            raise AppError(
                409, "REQUEST_RESOURCE_UNAVAILABLE", "Original resource is no longer available"
            )
        return resource
    # The callback must flush but not commit: receipt and resource are atomic.
    resource = await create()
    db.add(
        UIRequest(
            user_id=user_id,
            request_id=key,
            operation=operation,
            payload_hash=request_hash,
            resource_id=resource.id,
        )
    )
    await db.commit()
    return resource
