"""Bounded, idempotent local alert/brief dispatch; the scheduler never calls an LLM."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.assistant.orchestration import cleanup_chats
from app.core.valkey import make_valkey_client
from app.db.session import get_engine, get_session_factory
from app.jobs.celery_app import celery_app
from app.models import AlertRule, DailyBrief, DailyBriefConfig
from app.schemas.assistant import BriefConfigInput
from app.services.alerts import AlertEvaluationService
from app.services.daily_brief import DailyBriefService, due_period
from app.services.work_limits import work_slot


async def dispatch() -> dict[str, int]:
    counts = {"alerts": 0, "briefs": 0, "failed": 0}
    async with get_session_factory()() as db:
        async with work_slot(608715):
            now = datetime.now(UTC)
            rules = (
                await db.execute(
                    select(AlertRule.id, AlertRule.user_id)
                    .where(
                        AlertRule.archived.is_(False),
                        (AlertRule.last_checked_at.is_(None))
                        | (AlertRule.last_checked_at < now - timedelta(minutes=5)),
                    )
                    .order_by(AlertRule.last_checked_at.asc().nullsfirst())
                    .limit(50)
                )
            ).all()
            for identifier, user_id in rules:
                try:
                    async with asyncio.timeout(15):
                        await AlertEvaluationService(db, user_id).evaluate(identifier)
                    counts["alerts"] += 1
                except Exception:
                    await db.rollback()
                    counts["failed"] += 1
            configs = (
                await db.scalars(
                    select(DailyBriefConfig).where(DailyBriefConfig.enabled.is_(True)).limit(100)
                )
            ).all()
            # Capture primitives before any rollback expires ORM rows.
            settings = [(r.user_id, r.local_time, r.timezone) for r in configs]
            for user_id, local_time, timezone in settings:
                if counts["briefs"] >= 5:
                    break
                config = BriefConfigInput(enabled=True, local_time=local_time, timezone=timezone)
                day, _ = due_period(now, config)
                if await db.scalar(
                    select(DailyBrief.id).where(
                        DailyBrief.user_id == user_id, DailyBrief.local_date == day
                    )
                ):
                    continue
                try:
                    async with work_slot(608712), asyncio.timeout(90):
                        await DailyBriefService(db, user_id).generate()
                    counts["briefs"] += 1
                except Exception:
                    await db.rollback()
                    counts["failed"] += 1
    return counts


@celery_app.task(name="intelligence.dispatch", soft_time_limit=540, time_limit=570)  # type: ignore[misc]
def dispatch_task() -> dict[str, int]:
    async def run() -> dict[str, int]:
        try:
            counts = await dispatch()
            client = make_valkey_client()
            try:
                await client.set(
                    "intelligence:last-dispatch",
                    json.dumps({"completed_at": datetime.now(UTC).timestamp(), **counts}),
                    ex=900,
                )
            finally:
                await client.aclose()
            return counts
        finally:
            await get_engine().dispose()

    return asyncio.run(run())


@celery_app.task(name="assistant.cleanup_chats")  # type: ignore[misc]
def cleanup_task() -> dict[str, Any]:
    async def run() -> int:
        try:
            async with get_session_factory()() as db:
                return await cleanup_chats(db)
        finally:
            await get_engine().dispose()

    return {"removed": asyncio.run(run())}
