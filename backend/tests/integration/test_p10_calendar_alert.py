import asyncio
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AlertRule,
    AlertRuleVersion,
    DataSource,
    FinancialEventVersion,
    Instrument,
    Notification,
    RawIngestion,
    User,
)
from app.schemas.assistant import AlertRuleInput
from app.services.alerts import AlertEvaluationService
from app.services.auth import AuthService
from app.services.financial_events import FinancialEventService
from app.services.raw_ingestion import RawIngestionService


@pytest.mark.integration
def test_reviewed_calendar_exact_original_alert_dedup_correction_and_rights_withdrawal(monkeypatch):
    async def run():
        uid, iid, sid = uuid4(), uuid4(), uuid4()
        async with get_session_factory()() as db:
            try:
                user = await AuthService(db).create_user(
                    "p10_" + uuid4().hex[:12], secrets.token_urlsafe(32)
                )
                uid = user.id
                monkeypatch.setattr(get_settings(), "data_operator_usernames", [user.username])
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC calendar TEST",
                        ticker="CAL" + uuid4().hex[:8],
                        asset_type="STOCK",
                        currency="CHF",
                    )
                )
                source = DataSource(
                    id=sid,
                    name="SYNTHETIC calendar fixture",
                    slug="TEST_P10_" + uuid4().hex[:12].upper(),
                    type="MANUAL",
                    trust_level="C",
                    enabled=True,
                    gate_status="APPROVED",
                    checked_at=datetime.now(UTC),
                    allowed_uses=["CALENDAR_EVENTS"],
                )
                db.add(source)
                await db.commit()
                slug = source.slug
                calendar = FinancialEventService(db, uid)
                payload = {
                    "instrument_id": str(iid),
                    "event_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                    "event_type": "EARNINGS",
                    "status": "SCHEDULED",
                    "evidence_note": (
                        "Self-authored synthetic schedule used only to test "
                        "event provenance and alerts."
                    ),
                }
                original = json.dumps(payload, indent=2).encode()
                event = await calendar.import_bytes(slug, original, user)
                assert (
                    await RawIngestionService(db).get_verified(event.raw_ingestion_id) == original
                )
                service = AlertEvaluationService(db, uid)
                version = await service.save(
                    AlertRuleInput(
                        name="TEST upcoming",
                        type="EARNINGS_UPCOMING",
                        instrument_id=iid,
                        threshold=2,
                        direction="BELOW",
                    )
                )
                rid = version.rule_id
                first = await service.evaluate(rid)
                assert first and first.state is True
                first_id = first.id
                assert (await AlertEvaluationService(db, uid).evaluate(rid)).id == first_id
                assert (
                    await db.scalar(
                        select(func.count())
                        .select_from(Notification)
                        .where(Notification.user_id == uid)
                    )
                    == 1
                )
                payload.update(status="CANCELLED", replaces_id=str(event.id))
                correction = await calendar.import_bytes(slug, json.dumps(payload).encode(), user)
                assert [e.id for e in await calendar.available(datetime.now(UTC), iid)] == [
                    correction.id
                ]
                cancelled = await service.evaluate(rid)
                assert cancelled and cancelled.state is False and cancelled.result["value"] is None
                source.enabled = False
                await db.commit()
                unavailable = await service.evaluate(rid)
                assert unavailable and unavailable.status == "ALERT_EVALUATION_UNAVAILABLE"
                assert (
                    await db.scalar(
                        select(func.count())
                        .select_from(AlertEvent)
                        .where(AlertEvent.user_id == uid)
                    )
                    == 1
                )
            finally:
                await db.rollback()
                for model in (
                    Notification,
                    AlertEvent,
                    AlertEvaluation,
                    AlertRuleVersion,
                    AlertRule,
                    FinancialEventVersion,
                ):
                    await db.execute(delete(model).where(model.user_id == uid))
                await db.execute(delete(Instrument).where(Instrument.id == iid))
                await db.execute(delete(RawIngestion).where(RawIngestion.source_id == sid))
                await db.execute(delete(DataSource).where(DataSource.id == sid))
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
