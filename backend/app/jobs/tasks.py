from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.db.session import get_session_factory
from app.jobs.celery_app import celery_app
from app.repositories.core import delete_old_sessions


@celery_app.task(name="system.ping")  # type: ignore[misc]
def system_ping() -> dict[str, str]:
    return {"status": "ok", "executed_at": datetime.now(UTC).isoformat()}


@celery_app.task(name="auth.cleanup_sessions")  # type: ignore[misc]
def cleanup_sessions() -> dict[str, int]:
    async def run() -> int:
        async with get_session_factory()() as db:
            removed = await delete_old_sessions(db, older_than=datetime.now(UTC))
            await db.commit()
            return removed

    return {"removed": asyncio.run(run())}
