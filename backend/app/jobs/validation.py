"""Opt-in forward research; no source acquisition or model promotion."""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.jobs.celery_app import celery_app
from app.models import User, ValidationRecord
from app.services.forward_validation import ForwardValidationService
from app.services.validation_records import ValidationRecords


async def dispatch() -> dict[str, int]:
    result = {"policies": 0, "failed": 0}
    if not get_settings().forward_shadow_enabled:
        return result
    async with get_session_factory()() as db:
        attempt = aliased(ValidationRecord)
        last_attempt = (
            select(func.max(attempt.created_at))
            .where(
                attempt.parent_id == ValidationRecord.id, attempt.kind == "FORWARD_DISPATCH_ATTEMPT"
            )
            .correlate(ValidationRecord)
            .scalar_subquery()
        )
        current_enabled = (
            select(attempt.result["enabled"].as_boolean())
            .where(attempt.parent_id == ValidationRecord.id, attempt.kind == "FORWARD_POLICY_STATE")
            .order_by(attempt.created_at.desc(), attempt.id.desc())
            .limit(1)
            .correlate(ValidationRecord)
            .scalar_subquery()
        )
        policies = (
            await db.scalars(
                select(ValidationRecord)
                .join(User, User.id == ValidationRecord.user_id)
                .where(
                    ValidationRecord.kind == "FORWARD_POLICY",
                    User.is_active.is_(True),
                    User.username.in_(get_settings().ml_operator_usernames),
                    func.coalesce(
                        current_enabled,
                        ValidationRecord.request["scheduling_enabled"].as_boolean(),
                        False,
                    ).is_(True),
                )
                .order_by(last_attempt.asc().nulls_first(), ValidationRecord.created_at)
                .limit(1000)
            )
        ).all()
        users = set()
        policy_refs = [(p.id, p.user_id, p.request["scheduling_enabled"]) for p in policies]
        for policy_id, user_id, initial_enabled in policy_refs:
            state = await db.scalar(
                select(ValidationRecord)
                .where(
                    ValidationRecord.parent_id == policy_id,
                    ValidationRecord.kind == "FORWARD_POLICY_STATE",
                )
                .order_by(ValidationRecord.created_at.desc(), ValidationRecord.id.desc())
                .limit(1)
            )
            if not (state.result["enabled"] if state else initial_enabled):
                continue
            if result["policies"] + result["failed"] >= 10:
                break
            user = await db.get(User, user_id)
            if (
                not user
                or not user.is_active
                or user.username not in get_settings().ml_operator_usernames
            ):
                continue
            try:
                async with asyncio.timeout(180):
                    await ForwardValidationService(db, user).run(policy_id)
                users.add(user_id)
                result["policies"] += 1
            except Exception:
                await db.rollback()
                result["failed"] += 1
            finally:
                await ValidationRecords(db, user_id).append(
                    "FORWARD_DISPATCH_ATTEMPT", {}, {"status": "ATTEMPTED"}, parent_id=policy_id
                )
        for user_id in users:
            user = await db.get(User, user_id)
            assert user
            try:
                async with asyncio.timeout(180):
                    await ForwardValidationService(db, user).outcomes()
            except Exception:
                await db.rollback()
                result["failed"] += 1
    return result


@celery_app.task(name="validation.forward_dispatch")  # type: ignore[misc]
def forward_dispatch() -> dict[str, int]:
    async def run() -> dict[str, int]:
        try:
            return await dispatch()
        finally:
            await get_engine().dispose()

    return asyncio.run(run())
