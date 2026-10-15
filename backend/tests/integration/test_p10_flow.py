import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.assistant.documents import DocumentService
from app.assistant.runtime import TestOnlyProvider
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AlertRule,
    AlertRuleVersion,
    AssistantConversation,
    AuditEvent,
    ChunkEmbedding,
    DailyBrief,
    DailyBriefConfig,
    DataSource,
    DocumentChunk,
    DocumentRightsReview,
    Instrument,
    Notification,
    Portfolio,
    RawIngestion,
    ResearchDocument,
    SessionRecord,
    User,
)
from app.schemas.assistant import (
    DocumentMetadata,
    DocumentRightsInput,
    RetrievalInput,
    TimeMachineInput,
)
from app.services.auth import AuthService
from app.services.time_machine import TimeMachineService
from tests.unit.test_p10_contracts import pdf_bytes


@pytest.mark.integration
def test_private_assistant_alert_dedup_brief_without_llm_and_foreign_access(monkeypatch):
    stub = TestOnlyProvider()
    monkeypatch.setattr("app.assistant.orchestration.provider", lambda: stub)
    monkeypatch.setattr("app.assistant.documents.provider", lambda: stub)

    async def run():
        users, portfolios = [], []
        iid = uuid4()
        async with get_session_factory()() as db:
            try:
                password = secrets.token_urlsafe(32)
                first = await AuthService(db).create_user("p10_" + uuid4().hex[:12], password)
                other = await AuthService(db).create_user("p10_" + uuid4().hex[:12], password)
                users = [first.id, other.id]
                usernames = [first.username, other.username]
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC P10 TEST missing data",
                        ticker="P10" + uuid4().hex[:6],
                        currency="CHF",
                        asset_type="STOCK",
                    )
                )
                await db.commit()
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app()),
                    base_url="http://testserver",
                    headers={"Origin": get_settings().frontend_origin},
                    timeout=120,
                ) as client:
                    assert (await client.get("/api/v1/notifications")).status_code == 401
                    assert (
                        await client.post(
                            "/api/v1/auth/login",
                            json={"username": usernames[0], "password": password},
                        )
                    ).status_code == 200
                    portfolio = (
                        await client.post(
                            "/api/v1/portfolios",
                            json={"name": "SYNTHETIC P10", "base_currency": "CHF"},
                        )
                    ).json()["id"]
                    portfolios.append(UUID(portfolio))
                    historical = await client.post(
                        "/api/v1/time-machine",
                        json={"portfolio_id": portfolio, "as_of": "2020-01-01T12:00:00Z"},
                    )
                    assert (
                        historical.json()["sections"]["portfolio"]["status"]
                        == "NOT_ARCHIVED_AT_SELECTED_DATE"
                    )
                    assert historical.json()["sections"]["portfolio"]["value"] is None
                    old_tool = await client.post(
                        "/api/v1/assistant/tools/invoke",
                        json={
                            "name": "getPortfolio",
                            "portfolio_id": portfolio,
                            "as_of": "2020-01-01T12:00:00Z",
                        },
                    )
                    assert old_tool.json()[0]["fact_type"] == "UNAVAILABLE"

                    conv = (
                        await client.post(
                            "/api/v1/assistant/conversations", json={"title": "TEST private"}
                        )
                    ).json()["id"]
                    response = await client.post(
                        f"/api/v1/assistant/conversations/{conv}/messages",
                        json={
                            "question": "Empfehlung kaufen? password=hunter2",
                            "portfolio_id": portfolio,
                            "instrument_id": str(iid),
                        },
                    )
                    assert response.status_code == 200, response.text
                    assert "hunter2" not in response.text
                    assert "NO_VALIDATED_PRODUCTION_FORECAST" in response.text
                    assert '"type": "done"' in response.text
                    records = (
                        await client.get(f"/api/v1/assistant/conversations/{conv}/messages")
                    ).json()
                    assert len(records) == 2 and records[-1]["model_version"].startswith(
                        "TEST_ONLY"
                    )
                    assert "hunter2" not in str(records)
                    assert (
                        await client.post(
                            "/api/v1/assistant/tools/invoke", json={"name": "executeSQL"}
                        )
                    ).status_code == 422
                    version = (
                        await client.post(
                            "/api/v1/alert-rules",
                            json={
                                "name": "TEST missing forecast",
                                "type": "FORECAST_CHANGED",
                                "instrument_id": str(iid),
                                "threshold": ".1",
                                "direction": "ABSOLUTE_CHANGE",
                            },
                        )
                    ).json()
                    rule = version["rule_id"]
                    evaluation = (await client.post(f"/api/v1/alert-rules/{rule}/evaluate")).json()
                    assert (
                        evaluation["status"] == "ALERT_EVALUATION_UNAVAILABLE"
                        and evaluation["state"] is None
                    )
                    repeated = (await client.post(f"/api/v1/alert-rules/{rule}/evaluate")).json()
                    assert repeated["id"] == evaluation["id"]
                    assert (await client.get("/api/v1/alert-events")).json() == []
                    brief = await client.post("/api/v1/daily-brief/generate")
                    assert brief.status_code == 200, brief.text
                    bid = brief.json()["id"]
                    assert brief.json()["result"]["model_required"] is False
                    assert (await client.post("/api/v1/daily-brief/generate")).json()["id"] == bid
                    notifications = (await client.get("/api/v1/notifications")).json()
                    assert notifications["unread_count"] == 1
                    nid = notifications["items"][0]["id"]
                    assert (
                        await client.post(f"/api/v1/notifications/{nid}/read")
                    ).status_code == 200
                    assert (await client.get("/api/v1/notifications")).json()["unread_count"] == 0
                    await client.post("/api/v1/auth/logout")
                    await client.post(
                        "/api/v1/auth/login", json={"username": usernames[1], "password": password}
                    )
                    for path in (
                        f"/assistant/conversations/{conv}/messages",
                        f"/alert-rules/{rule}/evaluations",
                        f"/daily-brief/{bid}",
                    ):
                        assert (await client.get("/api/v1" + path)).status_code == 404
                    assert (
                        await client.post(f"/api/v1/notifications/{nid}/read")
                    ).status_code == 404
                    assert (
                        await client.post(
                            "/api/v1/time-machine",
                            json={
                                "portfolio_id": portfolio,
                                "as_of": datetime.now(UTC).isoformat(),
                            },
                        )
                    ).status_code == 404
                    await client.post("/api/v1/auth/logout")
                    await client.post(
                        "/api/v1/auth/login", json={"username": usernames[0], "password": password}
                    )
                    assert (
                        await client.delete(f"/api/v1/assistant/conversations/{conv}")
                    ).status_code == 204
                    assert (
                        await client.get(f"/api/v1/assistant/conversations/{conv}/messages")
                    ).status_code == 404
                with pytest.raises(DBAPIError):
                    await db.execute(
                        update(DailyBrief)
                        .where(DailyBrief.id == UUID(bid))
                        .values(content_hash="changed")
                    )
                await db.rollback()
            finally:
                await db.rollback()
                for model in (
                    AssistantConversation,
                    Notification,
                    DailyBrief,
                    DailyBriefConfig,
                    AlertEvent,
                    AlertEvaluation,
                    AlertRuleVersion,
                    AlertRule,
                ):
                    await db.execute(delete(model).where(model.user_id.in_(users)))
                await db.execute(delete(Portfolio).where(Portfolio.id.in_(portfolios)))
                await db.execute(delete(Instrument).where(Instrument.id == iid))
                for model in (AuditEvent, SessionRecord):
                    column = model.actor_user_id if model is AuditEvent else model.user_id
                    await db.execute(delete(model).where(column.in_(users)))
                await db.execute(delete(User).where(User.id.in_(users)))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())


@pytest.mark.integration
def test_pdf_rights_exact_raw_retrieval_owner_cutoff_immutability_and_outages(monkeypatch):
    async def run():
        source_id, user_ids, raw_ids = uuid4(), [], []
        async with get_session_factory()() as db:
            try:
                first = await AuthService(db).create_user(
                    "p10_" + uuid4().hex[:12], secrets.token_urlsafe(32)
                )
                other = await AuthService(db).create_user(
                    "p10_" + uuid4().hex[:12], secrets.token_urlsafe(32)
                )
                uid, oid, username = first.id, other.id, first.username
                user_ids = [uid, oid]
                monkeypatch.setattr(get_settings(), "data_operator_usernames", [username])
                source = DataSource(
                    id=source_id,
                    slug="TEST_P10_" + uuid4().hex[:12].upper(),
                    name="SYNTHETIC local PDF test",
                    type="MANUAL",
                    trust_level="C",
                    enabled=False,
                    gate_status="UNKNOWN",
                )
                db.add(source)
                await db.commit()
                slug = source.slug
                service = DocumentService(db, uid, embeddings=TestOnlyProvider())
                payload = pdf_bytes()
                sha = hashlib.sha256(payload).hexdigest()
                request = DocumentRightsInput(
                    source_slug=slug,
                    document_hash=sha,
                    storage_allowed=True,
                    indexing_allowed=True,
                    retention_policy="INDEFINITE_STORAGE_APPROVED",
                    attribution="Synthetic integration fixture",
                    evidence=(
                        "This self-authored synthetic fixture permits storage and "
                        "indexing for local tests."
                    ),
                )
                with pytest.raises(AppError):
                    await service.review(request, first)
                source.enabled, source.gate_status, source.checked_at = (
                    True,
                    "APPROVED",
                    datetime.now(UTC),
                )
                source.allowed_uses = ["RAG_STORAGE", "RAG_INDEX", "RAG_METADATA"]
                await db.commit()
                rights = await service.review(request, first)
                cutoff = datetime.now(UTC)
                metadata = DocumentMetadata(
                    title="SYNTHETIC TEST injection document",
                    source_slug=slug,
                    rights_review_id=rights.id,
                    published_at=cutoff - timedelta(days=100),
                )
                with pytest.raises(AppError):
                    await service.import_pdf(metadata, payload + b"changed")
                document = await service.import_pdf(metadata, payload)
                did, rid = document.id, document.raw_ingestion_id
                raw_ids.append(rid)
                assert document.processing_status == "INDEXED"
                assert await service.original(did) == payload
                assert (await service.retrieve(RetrievalInput(query="synthetic")))["citations"][0][
                    "document_hash"
                ] == sha
                assert not (
                    await service.retrieve(RetrievalInput(query="synthetic", as_of=cutoff))
                )["citations"]
                assert not (
                    await DocumentService(db, oid, embeddings=TestOnlyProvider()).retrieve(
                        RetrievalInput(query="synthetic")
                    )
                )["citations"]
                with pytest.raises(AppError):
                    await DocumentService(db, oid).original(did)
                archive = await TimeMachineService(db, uid).inspect(TimeMachineInput(as_of=cutoff))
                assert archive["sections"]["documents"]["items"] == []
                with pytest.raises(DBAPIError):
                    await db.execute(
                        update(ResearchDocument)
                        .where(ResearchDocument.id == did)
                        .values(title="changed")
                    )
                await db.rollback()

                class DownEmbedding:
                    async def embed(self, texts):
                        raise AppError(503, "EMBEDDING_DOWN", "Test outage")

                down = DocumentService(db, uid, embeddings=DownEmbedding())
                assert (await down.retrieve(RetrievalInput(query="synthetic")))[
                    "reason"
                ] == "EMBEDDING_DOWN"
                source = await db.get(DataSource, source_id)
                source.allowed_uses = ["RAG_INDEX"]
                await db.commit()
                assert not (await service.retrieve(RetrievalInput(query="synthetic")))["citations"]
                source.enabled = False
                await db.commit()
                assert not (await service.retrieve(RetrievalInput(query="synthetic")))["citations"]
            finally:
                await db.rollback()
                docs = select(ResearchDocument.id).where(ResearchDocument.user_id.in_(user_ids))
                chunks = select(DocumentChunk.id).where(DocumentChunk.document_id.in_(docs))
                await db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunks)))
                await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(docs)))
                await db.execute(
                    delete(ResearchDocument).where(ResearchDocument.user_id.in_(user_ids))
                )
                await db.execute(
                    delete(DocumentRightsReview).where(DocumentRightsReview.user_id.in_(user_ids))
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raw_ids)))
                await db.execute(delete(DataSource).where(DataSource.id == source_id))
                for model in (AuditEvent, SessionRecord):
                    column = model.actor_user_id if model is AuditEvent else model.user_id
                    await db.execute(delete(model).where(column.in_(user_ids)))
                await db.execute(delete(User).where(User.id.in_(user_ids)))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
