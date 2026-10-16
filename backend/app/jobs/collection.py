import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.jobs.celery_app import celery_app
from app.models import CollectorJob, Instrument, User
from app.schemas.data_operations import CollectionInput
from app.services.backfill_jobs import BackfillJobService
from app.services.market_calendar import MarketCalendarService
from app.services.work_limits import work_slot


async def dispatch() -> dict[str, int]:
    result = {"completed": 0, "failed": 0, "skipped": 0}
    async with work_slot(917002):
        async with get_session_factory()() as db:
            settings = get_settings()
            if settings.data_collection_enabled:
                for spec in json.loads(settings.data_collection_schedules)[:10]:
                    try:
                        user = (
                            await db.scalars(select(User).where(User.username == spec["operator"]))
                        ).one()
                        now = datetime.now(UTC)
                        end = now.date() - timedelta(days=1)
                        if spec["request"]["kind"] == "ALPHA_PRICES":
                            instrument = await db.get(
                                Instrument, UUID(spec["request"]["instrument_ids"][0])
                            )
                            if not instrument:
                                continue
                            calendar = MarketCalendarService()
                            exchange = instrument.exchange or instrument.mic or ""
                            sessions = calendar.sessions_between(
                                exchange, now.date() - timedelta(days=14), now.date()
                            )
                            published = [
                                day
                                for day in sessions
                                if calendar.session_close(exchange, day) + timedelta(minutes=90)
                                <= now
                            ]
                            if not published:
                                continue
                            end = published[-1]
                        request = CollectionInput.model_validate(
                            {
                                **spec["request"],
                                "start": (end - timedelta(days=31)).isoformat(),
                                "end": end.isoformat(),
                            }
                        )
                        if await db.scalar(
                            select(CollectorJob.id).where(
                                CollectorJob.configuration == request.model_dump(mode="json"),
                                CollectorJob.created_at >= datetime.now(UTC) - timedelta(hours=24),
                            )
                        ):
                            continue
                        await BackfillJobService(db, user).start(request)
                    except Exception:
                        await db.rollback()
                        result["skipped"] += 1
            # A RUNNING row with no advisory worker lock is recoverable after worker death.
            jobs = (
                await db.scalars(
                    select(CollectorJob)
                    .where(CollectorJob.status.in_(["QUEUED", "RUNNING"]))
                    .order_by(CollectorJob.created_at)
                    .limit(4)
                )
            ).all()
            for job in jobs:
                try:
                    job_user = await db.get(User, job.user_id)
                    if (
                        job_user is None
                        or not job_user.is_active
                        or job_user.username not in get_settings().data_operator_usernames
                    ):
                        job.status, job.last_error_code = "SKIPPED", "DATA_OPERATOR_REQUIRED"
                        await db.commit()
                        continue
                    row = await BackfillJobService(db, job_user).execute(job.id)
                    result["completed" if row.status == "SUCCESS" else "failed"] += 1
                except Exception:
                    await db.rollback()
                    result["failed"] += 1
    return result


@celery_app.task(name="data.collect_pending")  # type: ignore[misc]
def collect_pending() -> dict[str, int]:
    async def run() -> dict[str, int]:
        try:
            return await dispatch()
        finally:
            await get_engine().dispose()

    return asyncio.run(run())


@celery_app.task(name="data.collect_job")  # type: ignore[misc]
def collect_job(identifier: str) -> str:
    async def run() -> str:
        try:
            async with get_session_factory()() as db:
                job = await db.get(CollectorJob, UUID(identifier))
                if not job:
                    return "MISSING"
                user = await db.get(User, job.user_id)
                if (
                    not user
                    or not user.is_active
                    or user.username not in get_settings().data_operator_usernames
                ):
                    job.status, job.last_error_code = "SKIPPED", "DATA_OPERATOR_REQUIRED"
                    await db.commit()
                    return "DATA_OPERATOR_REQUIRED"
                return (await BackfillJobService(db, user).execute(job.id)).status
        finally:
            await get_engine().dispose()

    return asyncio.run(run())
