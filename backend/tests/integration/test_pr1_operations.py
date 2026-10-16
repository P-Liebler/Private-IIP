import asyncio
import json
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import partial
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.models import (
    AuditEvent,
    CollectorJob,
    DataCoverageSnapshot,
    DataQuarantine,
    DataSource,
    FundamentalFact,
    Instrument,
    MacroObservation,
    PriceDaily,
    PriceDailyVersion,
    ProviderSyncState,
    RawIngestion,
    SourceReviewEvidence,
    User,
)
from app.providers.alpha_vantage import AlphaVantageCollector
from app.providers.http import fetch_response
from app.providers.snb_fx import SnbFxCollector
from app.schemas.data_operations import CollectionInput
from app.services.auth import AuthService
from app.services.backfill_jobs import BackfillJobService
from app.services.ir_reports import IRReportReviewService, ReportReviewInput
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceService
from tests.integration.test_market_foundation import MemoryStorage
from tests.unit.test_pr1_providers import SNB


@pytest.fixture(autouse=True)
def isolated_provider_budget(monkeypatch):
    # Contract tests remain repeatable and do not consume the persistent shared
    # daily request budget. Dedicated limiter tests cover Valkey behavior.
    for module in ("snb_fx", "alpha_vantage"):
        monkeypatch.setattr(
            f"app.providers.{module}.fetch_response",
            partial(fetch_response, limiter=AsyncMock()),
        )


@pytest.mark.integration
def test_snb_raw_first_incremental_corrections_and_304() -> None:
    async def run() -> None:
        sid = uuid4()
        try:
            async with get_session_factory()() as db:
                source = DataSource(
                    id=sid,
                    slug="TEST_PR1_" + uuid4().hex[:12],
                    name="SYNTHETIC SNB CONTRACT",
                    type="OFFICIAL",
                    trust_level="A",
                    priority=20,
                    enabled=True,
                    gate_status="APPROVED",
                    checked_at=datetime.now(UTC),
                    next_review_at=datetime.now(UTC) + timedelta(days=1),
                    terms_url="https://example.org/synthetic",
                    decision_by="offline-test",
                    scope="synthetic fixtures only",
                    allowed_uses=["macro"],
                    rate_limit_per_minute=100,
                    failure_count=0,
                )
                db.add(source)
                await db.commit()
                storage = MemoryStorage()
                raw_service = RawIngestionService(db, storage)
                current = {"body": SNB, "status": 200, "etag": '"one"'}
                requests = []

                def handler(request: httpx.Request) -> httpx.Response:
                    requests.append(request)
                    return httpx.Response(
                        current["status"],
                        content=current["body"],
                        headers={"Content-Type": "text/csv", "ETag": current["etag"]},
                    )

                try:
                    with patch.object(SourceService, "get", new=AsyncMock(return_value=source)):
                        async with httpx.AsyncClient(
                            transport=httpx.MockTransport(handler)
                        ) as client:
                            collector = SnbFxCollector(db, client=client, raw_service=raw_service)
                            first = await collector.collect(date(2024, 1, 1), date(2024, 1, 31))
                            assert first["inserted"] == 1
                            assert await raw_service.get_verified(first["raw_ingestion_id"]) == SNB
                            repeat = await collector.collect(date(2024, 1, 1), date(2024, 1, 31))
                            assert repeat["status"] == "NO_NEW_DATA"
                            assert requests[1].headers["if-none-match"] == '"one"'
                            current.update(body=SNB.replace(b'"1.75"', b'"1.50"'), etag='"two"')
                            revised = await collector.collect(date(2024, 1, 1), date(2024, 1, 31))
                            assert revised["inserted"] == 1
                            rows = (
                                await db.scalars(
                                    select(MacroObservation)
                                    .where(MacroObservation.source_id == sid)
                                    .order_by(MacroObservation.observed_at)
                                )
                            ).all()
                            assert len(rows) == 2 and rows[1].replaces_id == rows[0].id
                            assert rows[0].known_at.year >= 2026 and rows[0].frequency == "M"
                            current.update(status=304, body=b"")
                            state = (
                                await db.scalars(
                                    select(ProviderSyncState).where(
                                        ProviderSyncState.source_id == sid
                                    )
                                )
                            ).one()
                            previous_raw, previous_success = (
                                state.raw_ingestion_id,
                                state.last_success_at,
                            )
                            assert (await collector.collect(date(2024, 1, 1), date(2024, 1, 31)))[
                                "status"
                            ] == "NO_NEW_DATA"
                            assert state.raw_ingestion_id == previous_raw
                            assert state.last_success_at > previous_success
                            assert (
                                await db.scalar(
                                    select(func.count())
                                    .select_from(MacroObservation)
                                    .where(MacroObservation.source_id == sid)
                                )
                                == 2
                            )
                            current.update(status=200, body=b"malformed")
                            with pytest.raises(AppError):
                                await collector.collect(date(2024, 1, 1), date(2024, 1, 31))
                            assert (
                                await db.scalar(
                                    select(func.count())
                                    .select_from(RawIngestion)
                                    .where(RawIngestion.source_id == sid)
                                )
                                == 5
                            )
                finally:
                    await db.rollback()
                    for model in (ProviderSyncState, MacroObservation, RawIngestion):
                        await db.execute(delete(model).where(model.source_id == sid))
                    await db.execute(delete(DataSource).where(DataSource.id == sid))
                    await db.commit()
        finally:
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_pdf_report_requires_review_and_preserves_corrected_human_confirmation(monkeypatch) -> None:
    async def run() -> None:
        uid, iid, sid = uuid4(), uuid4(), uuid4()
        try:
            async with get_session_factory()() as db:
                user = await AuthService(db).create_user(
                    "pr1ir_" + uuid4().hex[:10], secrets.token_urlsafe(24)
                )
                uid = user.id
                monkeypatch.setattr(get_settings(), "data_operator_usernames", [user.username])
                source = DataSource(
                    id=sid,
                    slug="TEST_PR1_IR_" + uuid4().hex[:8].upper(),
                    name="SYNTHETIC IR",
                    type="MANUAL",
                    trust_level="D",
                    enabled=True,
                    gate_status="APPROVED",
                    checked_at=datetime.now(UTC),
                    allowed_uses=["fundamentals", "filings"],
                )
                db.add_all(
                    [
                        source,
                        Instrument(id=iid, name="SYNTHETIC IR", asset_type="STOCK", currency="CHF"),
                    ]
                )
                await db.commit()
                try:
                    service = IRReportReviewService(db, user)
                    service.raw = RawIngestionService(db, MemoryStorage())
                    original = await service.upload(
                        source.slug,
                        iid,
                        b"%PDF-SYNTHETIC ONLY; parser stubbed in this workflow test",
                    )
                    with patch(
                        "app.services.ir_reports.parse_pdf",
                        new=AsyncMock(
                            return_value=[{"page": 1, "text": "Revenue CHF 100; corrected 90"}]
                        ),
                    ):
                        preview = await service.preview(original.id)
                        assert preview["canonical_facts_created"] == 0
                        request = ReportReviewInput.model_validate(
                            {
                                "reviewed": True,
                                "document_reference": "SYNTHETIC annual report 2024",
                                "candidates": [
                                    {
                                        "fact": {
                                            "instrument_id": str(iid),
                                            "metric": "revenue",
                                            "value": "100",
                                            "unit": "MONEY",
                                            "currency": "CHF",
                                            "period_start": "2024-01-01",
                                            "period_end": "2024-12-31",
                                            "period_type": "ANNUAL",
                                            "filing_reference": "SYNTHETIC-2024",
                                        },
                                        "page": 1,
                                        "quotation": "invented quotation",
                                        "accounting_basis": "SWISS_GAAP_FER",
                                        "definition": "Consolidated reported revenue",
                                    }
                                ],
                            }
                        )
                        with pytest.raises(AppError):
                            await service.commit(original.id, request)
                        request.candidates[0].quotation = "Revenue CHF 100"
                        assert (await service.commit(original.id, request))["inserted"] == 1
                        assert (await service.commit(original.id, request))["unchanged"] == 1
                        request.candidates[0].fact.value = Decimal("90")
                        request.candidates[0].quotation = "corrected 90"
                        assert (await service.commit(original.id, request))["restated"] == 1
                        facts = (
                            await db.scalars(
                                select(FundamentalFact)
                                .where(FundamentalFact.instrument_id == iid)
                                .order_by(FundamentalFact.observed_at)
                            )
                        ).all()
                        assert len(facts) == 2 and facts[1].replaces_version_id == facts[0].id
                        assert all(f.raw_ingestion_id != original.id for f in facts)
                finally:
                    await db.rollback()
                    for model, condition in (
                        (DataQuarantine, DataQuarantine.instrument_id == iid),
                        (FundamentalFact, FundamentalFact.instrument_id == iid),
                        (RawIngestion, RawIngestion.source_id == sid),
                        (Instrument, Instrument.id == iid),
                        (DataSource, DataSource.id == sid),
                        (AuditEvent, AuditEvent.actor_user_id == uid),
                        (User, User.id == uid),
                    ):
                        await db.execute(delete(model).where(condition))
                    await db.commit()
        finally:
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_optional_price_collector_canonical_correction_and_quarantine(monkeypatch) -> None:
    async def run() -> None:
        sid, iid = uuid4(), uuid4()
        try:
            async with get_session_factory()() as db:
                source = DataSource(
                    id=sid,
                    slug="TEST_PR1_PRICE_" + uuid4().hex[:8].upper(),
                    name="SYNTHETIC raw price contract",
                    type="MANUAL",
                    trust_level="D",
                    priority=100,
                    enabled=True,
                    gate_status="APPROVED",
                    checked_at=datetime.now(UTC),
                    scope=f"instrument={iid}",
                    allowed_uses=["prices"],
                    rate_limit_per_minute=100,
                    failure_count=0,
                )
                instrument = Instrument(
                    id=iid,
                    ticker="SYNTHETIC",
                    name="SYNTHETIC PR1 PRICE",
                    asset_type="STOCK",
                    currency="CHF",
                    exchange="SIX",
                )
                db.add_all([source, instrument])
                await db.commit()
                monkeypatch.setattr(
                    get_settings(), "alpha_vantage_api_key", SecretStr("offline-test-only")
                )
                payload = {
                    "Meta Data": {"2. Symbol": "SYNTHETIC"},
                    "Time Series (Daily)": {
                        "2024-01-03": {
                            "1. open": "99",
                            "2. high": "101",
                            "3. low": "98",
                            "4. close": "100",
                            "5. volume": "10",
                        }
                    },
                }
                storage = MemoryStorage()
                raw_service = RawIngestionService(db, storage)

                def handler(_request):
                    return httpx.Response(
                        200,
                        content=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"},
                    )

                try:
                    with patch.object(SourceService, "get", new=AsyncMock(return_value=source)):
                        async with httpx.AsyncClient(
                            transport=httpx.MockTransport(handler)
                        ) as client:
                            collector = AlphaVantageCollector(
                                db, client=client, raw_service=raw_service
                            )
                            assert (
                                await collector.collect(iid, date(2024, 1, 1), date(2024, 1, 5))
                            )["inserted"] == 1
                            assert (
                                await collector.collect(iid, date(2024, 1, 1), date(2024, 1, 5))
                            )["unchanged"] == 1
                            payload["Time Series (Daily)"]["2024-01-03"]["4. close"] = "100.1"
                            assert (
                                await collector.collect(iid, date(2024, 1, 1), date(2024, 1, 5))
                            )["corrected"] == 1
                            payload["Time Series (Daily)"]["2024-01-03"].update(
                                {"4. close": "500", "2. high": "501"}
                            )
                            result = await collector.collect(
                                iid, date(2024, 1, 1), date(2024, 1, 5)
                            )
                            assert result["quarantined"] == 1
                            price = await db.get(PriceDaily, (iid, date(2024, 1, 3)))
                            assert str(price.close) == "100.10000000"
                            assert (
                                await db.scalar(
                                    select(func.count())
                                    .select_from(PriceDailyVersion)
                                    .where(PriceDailyVersion.instrument_id == iid)
                                )
                                == 3
                            )
                finally:
                    await db.rollback()
                    for model, condition in (
                        (PriceDaily, PriceDaily.instrument_id == iid),
                        (DataQuarantine, DataQuarantine.instrument_id == iid),
                        (PriceDailyVersion, PriceDailyVersion.instrument_id == iid),
                        (RawIngestion, RawIngestion.source_id == sid),
                        (Instrument, Instrument.id == iid),
                        (DataSource, DataSource.id == sid),
                    ):
                        await db.execute(delete(model).where(condition))
                    await db.commit()
        finally:
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_jobs_private_recovery_cancel_coverage_and_immutable_reviews(monkeypatch) -> None:
    async def run() -> None:
        uid, iid, sid = uuid4(), uuid4(), uuid4()
        try:
            async with get_session_factory()() as db:
                user = await AuthService(db).create_user(
                    "pr1_" + uuid4().hex[:10], secrets.token_urlsafe(24)
                )
                uid = user.id
                monkeypatch.setattr(get_settings(), "data_operator_usernames", [user.username])
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC PR1 missing calendar",
                        asset_type="STOCK",
                        currency="CHF",
                    )
                )
                db.add(
                    DataSource(
                        id=sid,
                        name="SYNTHETIC RIGHTS REVIEW",
                        slug="TEST_PR1_" + uuid4().hex[:10].upper(),
                        type="MANUAL",
                        trust_level="D",
                        enabled=False,
                        gate_status="UNKNOWN",
                    )
                )
                await db.commit()
                source = await db.get(DataSource, sid)
                assert source
                slug = source.slug
                try:
                    await SourceService(db).review(
                        slug,
                        status="UNKNOWN",
                        terms_url=None,
                        scope="synthetic fixture only",
                        allowed_uses=[],
                        decision_note="No real provider rights granted by this fixture",
                        decision_by=user.username,
                        next_review_at=None,
                    )
                    review = (
                        await db.scalars(
                            select(SourceReviewEvidence).where(
                                SourceReviewEvidence.source_id == sid
                            )
                        )
                    ).one()
                    with pytest.raises(DBAPIError, match="PIT versions are immutable"):
                        await db.execute(
                            text("UPDATE source_review_evidence SET decision='{}' WHERE id=:id"),
                            {"id": review.id},
                        )
                    await db.rollback()
                    user = await db.get(User, uid)
                    assert user
                    service = BackfillJobService(db, user)
                    request = CollectionInput(
                        source_slug="MANUAL_CSV",
                        kind="COVERAGE",
                        start=date(2024, 1, 1),
                        end=date(2024, 1, 31),
                        instrument_ids=[iid],
                    )
                    job = await service.start(request)
                    jid = job.id
                    assert (await service.start(request)).id == jid
                    await service.control(jid, "cancel")
                    assert (await service.owned(jid)).status == "CANCELLED"
                    await service.control(jid, "resume")
                    completed = await service.execute(jid)
                    assert completed.status == "SUCCESS" and completed.progress == 1
                    assert completed.results[0]["coverage"][0]["state"] == "UNAVAILABLE"
                    assert (
                        completed.results[0]["coverage"][0]["price_coverage"]["expected_sessions"]
                        is None
                    )
                    count = await db.scalar(
                        select(func.count())
                        .select_from(DataCoverageSnapshot)
                        .where(DataCoverageSnapshot.user_id == uid)
                    )
                    await service.execute(jid)
                    assert (
                        await db.scalar(
                            select(func.count())
                            .select_from(DataCoverageSnapshot)
                            .where(DataCoverageSnapshot.user_id == uid)
                        )
                        == count
                    )
                    monkeypatch.setattr(get_settings(), "data_operator_usernames", [])
                    with pytest.raises(AppError) as denied:
                        await service.preview(request)
                    assert denied.value.code == "DATA_OPERATOR_REQUIRED"
                finally:
                    await db.rollback()
                    for model, condition in (
                        (CollectorJob, CollectorJob.user_id == uid),
                        (DataCoverageSnapshot, DataCoverageSnapshot.user_id == uid),
                        (SourceReviewEvidence, SourceReviewEvidence.source_id == sid),
                        (DataSource, DataSource.id == sid),
                        (Instrument, Instrument.id == iid),
                        (AuditEvent, AuditEvent.actor_user_id == uid),
                        (User, User.id == uid),
                    ):
                        await db.execute(delete(model).where(condition))
                    await db.commit()
        finally:
            await get_engine().dispose()

    asyncio.run(run())
