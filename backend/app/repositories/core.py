from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionRecord, User


async def find_user_by_username(
    db: AsyncSession, username: str, *, for_update: bool = False
) -> User | None:
    statement = select(User).where(User.username == username)
    if for_update:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def find_user_by_id(
    db: AsyncSession, user_id: UUID, *, for_update: bool = False
) -> User | None:
    statement = select(User).where(User.id == user_id)
    if for_update:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def find_session_by_hash(db: AsyncSession, token_hash: str) -> SessionRecord | None:
    return (
        await db.execute(select(SessionRecord).where(SessionRecord.token_hash == token_hash))
    ).scalar_one_or_none()


async def delete_old_sessions(db: AsyncSession, *, older_than: datetime) -> int:
    result = await db.execute(
        delete(SessionRecord)
        .where(or_(SessionRecord.expires_at < older_than, SessionRecord.revoked_at < older_than))
        .returning(SessionRecord.id)
    )
    return len(result.scalars().all())
