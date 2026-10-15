"""Persistent synthetic restore fixture. No real calendar/provider is enabled."""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import DailyBriefConfig, DataSource, User
from app.schemas.assistant import AlertRuleInput, BriefConfigInput
from app.services.alerts import AlertEvaluationService
from app.services.daily_brief import DailyBriefService
from app.services.financial_events import FinancialEventService


async def main() -> None:
    try:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == os.environ["E2E_USERNAME"]))
            assert user and user.username.startswith(("restore_", "p10_", "test_"))
            get_settings().data_operator_usernames = [user.username]
            source = DataSource(
                id=uuid4(),
                slug="TEST_CAL_" + uuid4().hex[:12].upper(),
                name="SYNTHETIC restore calendar",
                type="MANUAL",
                trust_level="C",
                gate_status="APPROVED",
                enabled=True,
                checked_at=datetime.now(UTC),
                allowed_uses=["CALENDAR_EVENTS"],
                scope="Only self-authored synthetic restore events",
                decision_by="explicit test fixture",
                decision_note="No real earnings schedule",
            )
            db.add(source)
            await db.commit()
            iid = UUID(os.environ["E2E_RESEARCH_INSTRUMENT_ID"])
            calendar = FinancialEventService(db, user.id)
            payload = {
                "instrument_id": str(iid),
                "event_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "event_type": "EARNINGS",
                "status": "SCHEDULED",
                "evidence_note": (
                    "SYNTHETIC self-authored restore fixture; this is not a real earnings date."
                ),
            }
            event = await calendar.import_bytes(source.slug, json.dumps(payload).encode(), user)
            config = AlertRuleInput(
                name="SYNTHETIC restore event, subsequently cancelled",
                type="EARNINGS_UPCOMING",
                instrument_id=iid,
                threshold=2,
                direction="BELOW",
            )
            alerts = AlertEvaluationService(db, user.id)
            version = await alerts.save(config)
            triggered = await alerts.evaluate(version.rule_id)
            assert triggered and triggered.state is True
            payload.update(status="CANCELLED", replaces_id=str(event.id))
            await calendar.import_bytes(source.slug, json.dumps(payload).encode(), user)
            cancelled = await alerts.evaluate(version.rule_id)
            assert cancelled and cancelled.state is False
            await alerts.save(config.model_copy(update={"enabled": False}), version.rule_id)
            if await db.get(DailyBriefConfig, user.id) is None:
                await DailyBriefService(db, user.id).configure(BriefConfigInput(enabled=False))
            print(
                json.dumps(
                    {
                        "calendar_versions": 2,
                        "alert_event": 1,
                        "rule_disabled": True,
                        "source_slug": source.slug,
                        "data_context": "SYNTHETIC_NOT_REAL_FINANCE",
                    }
                )
            )
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
