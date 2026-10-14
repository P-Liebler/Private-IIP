from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import PITJob


async def execute_job[T](
    db: AsyncSession, user_id: UUID, kind: str, work: Callable[[], Awaitable[T]]
) -> tuple[T, UUID]:
    job = PITJob(
        user_id=user_id, kind=kind, status="RUNNING", progress=0, started_at=datetime.now(UTC)
    )
    db.add(job)
    await db.commit()
    job_id = job.id
    locked = False
    for slot in range(get_settings().p6_max_concurrent_runs):
        if await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": 608620 + slot}):
            locked = True
            break
    try:
        if not locked:
            raise AppError(409, "RUN_LIMIT", "Concurrent P6 run limit reached")
        result = await work()
        job.status = "COMPLETED"
        job.progress = 100
        job.completed_at = datetime.now(UTC)
        await db.commit()
        return result, job_id
    except Exception as error:
        await db.rollback()
        persisted = await db.get(PITJob, job_id)
        assert persisted
        persisted.status = "FAILED"
        persisted.error_code = (
            error.code
            if isinstance(error, AppError)
            else "TIMEOUT"
            if isinstance(error, TimeoutError)
            else "BUILD_FAILED"
        )
        persisted.completed_at = datetime.now(UTC)
        await db.commit()
        raise
