from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text

from app.core.errors import AppError
from app.db.session import get_engine


@asynccontextmanager
async def work_slot(identifier: int) -> AsyncIterator[None]:
    """Dedicated session lock survives commits in domain services; always unlock it."""
    async with get_engine().connect() as connection:
        locked = await connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": identifier}
        )
        if not locked:
            raise AppError(409, "WORK_RESOURCE_LIMIT", "Another calculation is active")
        try:
            yield
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": identifier})
