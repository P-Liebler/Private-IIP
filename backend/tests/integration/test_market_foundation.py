from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AuditEvent, DataSource, Instrument, InstrumentIdentifier, PriceDaily,
    PriceDailyVersion, RawIngestion, User,
)
from app.providers.openfigi import MappingService, OpenFigiProvider
from app.services.auth import AuthService
from app.services.csv_preview import CsvPreviewService
from app.services.instruments import InstrumentService
from app.services.provider_rate_limit import check_provider_rate
from app.services.raw_ingestion import RawIngestionService, safe_request_metadata
from app.services.sources import SourceGate, SourceService


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail = False

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        if self.fail:
            raise OSError("storage unavailable")
        if key in self.objects:
            raise FileExistsError(key)
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def exists(self, key: str) -> bool:
        return key in self.objects

    def ensure_bucket(self) -> None:
        pass

    def delete(self, key: str) -> None:
        del self.objects[key]


def test_raw_metadata_rejects_secrets() -> None:
    assert safe_request_metadata({"endpoint": "/v3/mapping", "method": "POST"}) == {
        "endpoint": "/v3/mapping",
        "method": "POST",
    }
    for value in (
        {"api_key": "hidden"},
        {"endpoint": "/v3/mapping?token=secret"},
        {"filename": "unsafe\r\nname.csv"},
    ):
        with pytest.raises(ValueError):
            safe_request_metadata(value)


def test_raw_database_failure_writes_no_object() -> None:
    async def run() -> None:
        db = MagicMock(spec=AsyncSession)
        db.commit = AsyncMock(side_effect=OSError("database unavailable"))
        db.rollback = AsyncMock()
        storage = MemoryStorage()
        with pytest.raises(AppError) as exc:
            await RawIngestionService(db, storage).store(
                data=b"original",
                source_id=uuid4(),
                source_slug="manual_csv",
                resource_type="manual_csv_preview",
            )
        assert exc.value.code == "RAW_DATABASE_UNAVAILABLE"
        assert storage.objects == {}
        db.rollback.assert_awaited_once()

    asyncio.run(run())


@pytest.mark.integration
def test_shared_provider_rate_limit() -> None:
    async def run() -> None:
        source = DataSource(slug=f"TEST_{uuid4().hex}", rate_limit_per_minute=1)
        await check_provider_rate(source)
        with pytest.raises(AppError) as exc:
            await check_provider_rate(source)
        assert exc.value.code == "SOURCE_RATE_LIMITED" and exc.value.retry_after is not None

    asyncio.run(run())


def test_new_apis_require_session() -> None:
    async def run() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=create_app()), base_url="http://testserver"
        ) as client:
            for path in (
                "/api/v1/instruments/search?q=AAPL", "/api/v1/data-sources",
                f"/api/v1/instruments/{uuid4()}/prices",
                f"/api/v1/instruments/{uuid4()}/corporate-actions",
                "/api/v1/fx/rate?base=USD&quote=CHF&on_date=2024-01-02",
                "/api/v1/data-quality/summary",
            ):
                assert (await client.get(path)).status_code == 401
            assert (
                await client.post(
                    "/api/v1/instruments",
                    json={"name": "Test", "asset_type": "STOCK", "currency": "USD"},
                )
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/imports/csv/preview",
                    content=b"date,ticker,close\n",
                    headers={"Content-Type": "text/csv"},
                )
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/market-data/imports/prices/commit",
                    json={"raw_ingestion_id": str(uuid4()), "mapping": {}},
                )
            ).status_code == 401

    asyncio.run(run())


@pytest.mark.integration
def test_authenticated_instrument_and_csv_apis(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> None:
        storage = MemoryStorage()
        monkeypatch.setattr("app.services.raw_ingestion.get_storage", lambda: storage)
        username = f"api_p2_{uuid4().hex[:12]}"
        password = "test-only-long-password-2"
        ticker = f"T{uuid4().hex[:7].upper()}"
        instrument_id: UUID | None = None
        raw_id: UUID | None = None
        p3_raw_id: UUID | None = None
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(username, password)
            user_id = user.id
        try:
            async with AsyncClient(
                transport=ASGITransport(app=create_app()),
                base_url="http://testserver",
                headers={"Origin": get_settings().frontend_origin},
            ) as client:
                login = await client.post(
                    "/api/v1/auth/login", json={"username": username, "password": password}
                )
                assert login.status_code == 200
                created = await client.post(
                    "/api/v1/instruments",
                    json={
                        "name": "API fixture stock",
                        "asset_type": "STOCK",
                        "currency": "USD",
                        "ticker": ticker,
                    },
                )
                assert created.status_code == 201, created.text
                instrument_id = UUID(created.json()["id"])
                search = await client.get(f"/api/v1/instruments/search?q={ticker}")
                assert search.status_code == 200
                assert search.json()[0]["instrument"]["id"] == str(instrument_id)
                detail = await client.get(f"/api/v1/instruments/{instrument_id}")
                assert detail.status_code == 200
                assert detail.json()["identifiers"][0]["value"] == ticker
                changed = await client.patch(
                    f"/api/v1/instruments/{instrument_id}", json={"active": False}
                )
                assert changed.status_code == 200 and changed.json()["active"] is False
                sources = await client.get("/api/v1/data-sources")
                assert sources.status_code == 200
                assert {item["slug"] for item in sources.json()} >= {
                    "MANUAL_CSV",
                    "OPENFIGI",
                    "YAHOO",
                    "STOOQ",
                }
                assert (await client.get(f"/api/v1/instruments/{instrument_id}/prices")).json()["status"] == "UNAVAILABLE"
                assert (await client.get(f"/api/v1/instruments/{instrument_id}/corporate-actions")).status_code == 200
                assert (await client.get("/api/v1/fx/rate?base=USD&quote=CHF&on_date=1000-01-10")).json()["status"] == "UNAVAILABLE"
                assert (await client.get("/api/v1/data-quality/summary")).status_code == 200
                upload = await client.post(
                    "/api/v1/imports/csv/preview",
                    content=f"date,ticker,close\n{datetime.now(UTC).date()},{ticker},12.5\n".encode(),
                    headers={"Content-Type": "text/csv", "X-Filename": "fixture.csv"},
                )
                assert upload.status_code == 200, upload.text
                raw_id = UUID(upload.json()["raw_ingestion_id"])
                assert upload.json()["sample_rows"][0]["resolution_status"] == "RESOLVED"
                assert upload.json()["sample_rows"][0]["instrument_id"] == str(instrument_id)
                market_preview = await client.post(
                    "/api/v1/market-data/imports/prices/preview",
                    content=f"date,ticker,close,currency\n{datetime.now(UTC).date()},{ticker},12.5,USD\n".encode(),
                    headers={"Content-Type": "text/csv", "X-Filename": "p3-fixture.csv"},
                )
                assert market_preview.status_code == 200, market_preview.text
                p3_raw_id = UUID(market_preview.json()["raw_ingestion_id"])
                committed = await client.post(
                    "/api/v1/market-data/imports/prices/commit",
                    json={
                        "raw_ingestion_id": str(p3_raw_id),
                        "mapping": market_preview.json()["mapping"],
                    },
                )
                assert committed.status_code == 200, committed.text
                assert committed.json()["inserted"] == 1
                prices = await client.get(f"/api/v1/instruments/{instrument_id}/prices")
                assert prices.status_code == 200
                assert prices.json()["prices"][0]["close"] == 12.5
                assert prices.json()["prices"][0]["raw_ingestion_id"] == str(p3_raw_id)
        finally:
            async with get_session_factory()() as db:
                await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id == user_id))
                if instrument_id is not None:
                    await db.execute(delete(PriceDaily).where(PriceDaily.instrument_id == instrument_id))
                    await db.execute(
                        delete(PriceDailyVersion).where(
                            PriceDailyVersion.instrument_id == instrument_id
                        )
                    )
                    await db.execute(
                        delete(InstrumentIdentifier).where(
                            InstrumentIdentifier.instrument_id == instrument_id
                        )
                    )
                if raw_id is not None:
                    await db.execute(delete(RawIngestion).where(RawIngestion.id == raw_id))
                if p3_raw_id is not None:
                    await db.execute(delete(RawIngestion).where(RawIngestion.id == p3_raw_id))
                if instrument_id is not None:
                    await db.execute(delete(Instrument).where(Instrument.id == instrument_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_raw_instrument_csv_and_source_gate() -> None:
    async def run() -> None:
        storage = MemoryStorage()
        username = f"p2_{uuid4().hex[:12]}"
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(username, "test-only-long-password-2")
            user_id = user.id
        raw_ids: list[UUID] = []
        instrument_ids: list[UUID] = []
        try:
            async with get_session_factory()() as db:
                sources = SourceService(db)
                manual = await sources.get("MANUAL_CSV")
                assert manual.enabled and manual.gate_status == "APPROVED"
                for slug, status in (
                    ("YAHOO", "BLOCKED"),
                    ("STOOQ", "UNKNOWN"),
                    ("OPENFIGI", "UNKNOWN"),
                ):
                    source = await sources.get(slug)
                    assert source.gate_status == status and not source.enabled
                    with pytest.raises(AppError) as exc:
                        await sources.enable(slug)
                    assert exc.value.code == "SOURCE_NOT_APPROVED"
                raw_service = RawIngestionService(db, storage)
                data = b"date,ticker,close\n2026-10-01,AAPL,200.50\n"
                first = await raw_service.store(
                    data=data,
                    source_id=manual.id,
                    source_slug=manual.slug,
                    resource_type="manual_csv_preview",
                    content_type="text/csv",
                    request_metadata={"filename": "prices.csv"},
                )
                raw_ids.append(first.id)
                assert first.status == "STORED" and first.sha256 == hashlib.sha256(data).hexdigest()
                assert first.requested_at is None and first.http_status is None
                assert first.request_metadata == {"filename": "prices.csv"}
                assert await raw_service.get_verified(first.id) == data
                second = await raw_service.store(
                    data=data,
                    source_id=manual.id,
                    source_slug=manual.slug,
                    resource_type="manual_csv_preview",
                    content_type="text/csv",
                )
                raw_ids.append(second.id)
                assert first.object_path != second.object_path
                assert first.object_path is not None
                storage.objects[first.object_path] = b"tampered"
                with pytest.raises(AppError) as exc:
                    await raw_service.get_verified(first.id)
                assert exc.value.code == "RAW_INTEGRITY_ERROR"
                storage.fail = True
                with pytest.raises(AppError) as exc:
                    await raw_service.store(
                        data=b"failure",
                        source_id=manual.id,
                        source_slug=manual.slug,
                        resource_type="manual_csv_preview",
                    )
                assert exc.value.code == "RAW_STORAGE_UNAVAILABLE"
                failed = (
                    await db.scalars(
                        select(RawIngestion)
                        .where(RawIngestion.status == "FAILED", RawIngestion.source_id == manual.id)
                        .order_by(RawIngestion.created_at.desc())
                    )
                ).first()
                assert failed is not None and failed.object_path is not None
                raw_ids.append(failed.id)
                storage.fail = False

                instruments = InstrumentService(db)
                apple = await instruments.create(
                    name="Apple Inc.",
                    asset_type="STOCK",
                    currency="USD",
                    ticker=" aapl ",
                    isin="US0378331005",
                    figi="BBG000B9XRY4",
                    exchange="NASDAQ",
                    country="US",
                    listed_at=date(2020, 1, 1),
                    actor_user_id=user_id,
                )
                apple_id = apple.id
                instrument_ids.append(apple_id)
                assert isinstance(apple_id, UUID)
                for query in ("Apple", "AAPL", "US0378331005", "BBG000B9XRY4"):
                    hits = await instruments.search(query)
                    assert hits and hits[0].instrument.id == apple_id
                assert (await instruments.search("App"))[0].resolution_status == "CANDIDATE"
                before_conflicts = await db.scalar(select(func.count()).select_from(Instrument))
                for kind, value in (
                    ("ISIN", "US0378331005"),
                    ("FIGI", "BBG000B9XRY4"),
                    ("TICKER", "AAPL"),
                ):
                    with pytest.raises(AppError) as exc:
                        await instruments.create(
                            name=f"Duplicate {kind}",
                            asset_type="STOCK",
                            currency="USD",
                            exchange="NASDAQ",
                            actor_user_id=user_id,
                            **{kind.lower(): value},
                        )
                    assert exc.value.code == "IDENTIFIER_CONFLICT"
                assert (
                    await db.scalar(select(func.count()).select_from(Instrument))
                    == before_conflicts
                )
                changed = await instruments.set_identifier(
                    apple_id,
                    "TICKER",
                    "APPL",
                    valid_from=date(2026, 10, 2),
                    source_id=None,
                    raw_ingestion_id=None,
                    actor_user_id=user_id,
                )
                assert changed.value == "APPL" and apple_id == changed.instrument_id
                assert (await instruments.search("AAPL"))[0].current is False
                current, history = await instruments.get(apple_id)
                assert current.ticker == "APPL"
                assert any(i.value == "AAPL" and i.valid_to == date(2026, 10, 2) for i in history)
                second_stock = await instruments.create(
                    name="Second company",
                    asset_type="STOCK",
                    currency="USD",
                    ticker="APPL",
                    exchange="NYSE",
                    listed_at=date(2020, 1, 1),
                    actor_user_id=user_id,
                )
                instrument_ids.append(second_stock.id)
                hits = await instruments.search("APPL")
                assert len(hits) == 2 and all(h.resolution_status == "AMBIGUOUS" for h in hits)
                await instruments.update(
                    apple_id,
                    {"active": False, "delisted_at": date(2026, 10, 3)},
                    actor_user_id=user_id,
                )
                found = (await instruments.search("US0378331005"))[0].instrument
                assert found.id == apple_id and not found.active

                csv_service = CsvPreviewService(db, raw_service)
                preview = await csv_service.preview(data, filename="prices.csv")
                raw_ids.append(preview.raw_ingestion_id)
                assert preview.sample_rows[0].resolution_status == "RESOLVED"
                assert preview.sample_rows[0].instrument_id == apple_id
                assert preview.possible_mapping["close"] == "close"
                isin_preview = await csv_service.preview(
                    b"date,isin,close\n2026-10-01,US0378331005,200.5\n", filename="isin.csv"
                )
                raw_ids.append(isin_preview.raw_ingestion_id)
                assert isin_preview.sample_rows[0].instrument_id == apple_id
                for content, expected in (
                    (b"ticker,close\nAAPL,20\n", "Missing required column: date"),
                    (
                        b"date,ticker,close,strange\n2026-10-01,AAPL,20,x\n",
                        "Unknown column: strange",
                    ),
                    (b"date,ticker,close\n2026-10-01,UNKNOWN,20\n", "UNRESOLVED"),
                    (b"date,ticker,close\n2026-10-02,APPL,20\n", "AMBIGUOUS"),
                    (b"date,ticker,close\n2026-10-01,AAPL,invalid,extra\n", "Malformed row"),
                ):
                    result = await csv_service.preview(content, filename="test.csv")
                    raw_ids.append(result.raw_ingestion_id)
                    assert expected in str(result.validation_errors) + str(result.sample_rows)
                # Preview persists only raw_ingestions, never a canonical price table.
        finally:
            async with get_session_factory()() as db:
                await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id == user_id))
                await db.execute(
                    delete(InstrumentIdentifier).where(
                        InstrumentIdentifier.instrument_id.in_(instrument_ids)
                    )
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raw_ids)))
                await db.execute(delete(Instrument).where(Instrument.id.in_(instrument_ids)))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_openfigi_gate_and_mocked_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> None:
        storage = MemoryStorage()
        monkeypatch.setattr("app.services.raw_ingestion.get_storage", lambda: storage)
        calls: list[httpx.Request] = []
        fixture_figi = f"BBG{uuid4().hex[:9].upper()}"
        response_body = json.dumps(
            [{"data": [{"figi": fixture_figi, "ticker": "AAPL", "name": "Apple Inc."}]}]
        ).encode()
        body = response_body
        status = 200
        timeout = False

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if timeout:
                raise httpx.ReadTimeout("mock timeout")
            return httpx.Response(
                status, content=body, headers={"Content-Type": "application/json"}
            )

        async with get_session_factory()() as db:
            service = SourceService(db)
            source = await service.get("OPENFIGI")
            source_id = source.id
            if source.gate_status != "UNKNOWN" or source.checked_at is not None:
                await db.close()
                await get_engine().dispose()
                pytest.skip("OpenFIGI has an operator decision; fixture will not change it")
            original_raw_ids = set(
                (
                    await db.scalars(
                        select(RawIngestion.id).where(RawIngestion.source_id == source.id)
                    )
                ).all()
            )
            original_source_audit_ids = set(
                (
                    await db.scalars(
                        select(AuditEvent.id).where(AuditEvent.resource_id == str(source.id))
                    )
                ).all()
            )
            initial = {
                field: getattr(source, field)
                for field in (
                    "gate_status",
                    "enabled",
                    "terms_url",
                    "checked_at",
                    "scope",
                    "allowed_uses",
                    "decision_note",
                    "decision_by",
                    "next_review_at",
                    "rate_limit_per_minute",
                    "failure_count",
                    "last_failure",
                    "last_success",
                )
            }
            raw_ids: list[UUID] = []
            instrument_ids: list[UUID] = []
            username = f"mapping_{uuid4().hex[:12]}"
            user = await AuthService(db).create_user(username, "test-only-long-password-2")
            user_id = user.id
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                provider = OpenFigiProvider(
                    db, client=client, raw_service=RawIngestionService(db, storage)
                )
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_NOT_APPROVED" and calls == []
                source.gate_status = "BLOCKED"
                await db.commit()
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_NOT_APPROVED" and calls == []
                source.gate_status = "UNKNOWN"
                await db.commit()
                await service.review(
                    "OPENFIGI",
                    status="APPROVED",
                    terms_url="https://www.openfigi.com/api/documentation",
                    scope="test fixture only",
                    allowed_uses=["mapping"],
                    decision_note="test approval",
                    decision_by="pytest",
                    next_review_at=datetime.now(UTC) + timedelta(days=1),
                    rate_limit_per_minute=1000,
                )
                await service.enable("OPENFIGI")
                assert SourceGate.require_enabled(source, "mapping") is None
                result = await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert (
                    result.status == "UNIQUE_CANDIDATE"
                    and result.candidates[0].figi == fixture_figi
                )
                assert result.raw_ingestion_id is not None
                raw_ids.append(result.raw_ingestion_id)
                mapped = await InstrumentService(db).create(
                    name=f"Mapped {uuid4().hex[:8]}",
                    asset_type="STOCK",
                    currency="USD",
                    actor_user_id=user.id,
                )
                instrument_ids.append(mapped.id)
                assert mapped.figi is None  # A unique candidate still needs acceptance.
                with pytest.raises(AppError) as exc:
                    await MappingService(db).accept(
                        instrument_id=mapped.id,
                        raw_ingestion_id=result.raw_ingestion_id,
                        figi="BBG000B9XRY5",
                        actor_user_id=user.id,
                    )
                assert exc.value.code == "MAPPING_CANDIDATE_INVALID"
                await MappingService(db).accept(
                    instrument_id=mapped.id,
                    raw_ingestion_id=result.raw_ingestion_id,
                    figi=fixture_figi,
                    actor_user_id=user.id,
                )
                mapped, identifiers = await InstrumentService(db).get(mapped.id)
                assert mapped.figi == fixture_figi
                assert any(
                    item.value == fixture_figi
                    and item.raw_ingestion_id == result.raw_ingestion_id
                    and item.source_id == source.id
                    for item in identifiers
                )
                assert calls[0].url.path == "/v3/mapping"
                assert json.loads(calls[0].content) == [
                    {"idType": "ID_ISIN", "idValue": "US0378331005"}
                ]
                assert (
                    storage.objects[
                        (await db.get(RawIngestion, result.raw_ingestion_id)).object_path
                    ]
                    == response_body
                )  # type: ignore[union-attr,index]
                for response, expected in (
                    (b'[{"data":[{"figi":"BBG000B9XRY4"},{"figi":"BBG000B9XRY5"}]}]', "AMBIGUOUS"),
                    (b'[{"data":[]}]', "NO_MATCH"),
                ):
                    body = response
                    result = await provider.map_identifier(kind="ISIN", value="US0378331005")
                    assert result.status == expected and result.raw_ingestion_id is not None
                    raw_ids.append(result.raw_ingestion_id)
                body = b"not json"
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_RESPONSE_INVALID"
                for http_status, expected in (
                    (429, "SOURCE_RATE_LIMITED"),
                    (503, "SOURCE_UNAVAILABLE"),
                ):
                    status = http_status
                    with pytest.raises(AppError) as exc:
                        await provider.map_identifier(kind="ISIN", value="US0378331005")
                    assert exc.value.code == expected
                status = 200
                timeout = True
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_TIMEOUT"
                rows = (
                    await db.scalars(
                        select(RawIngestion).where(RawIngestion.source_id == source.id)
                    )
                ).all()
                assert any(
                    row.id not in original_raw_ids
                    and row.status == "FAILED"
                    and row.error == "SOURCE_TIMEOUT"
                    for row in rows
                )
                source.enabled = False
                await db.commit()
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_NOT_APPROVED"
                assert len(calls) == 7
                source.enabled = True
                source.next_review_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()
                with pytest.raises(AppError) as exc:
                    await provider.map_identifier(kind="ISIN", value="US0378331005")
                assert exc.value.code == "SOURCE_NOT_APPROVED" and len(calls) == 7
            finally:
                await client.aclose()
                await db.rollback()
                for field, value in initial.items():
                    setattr(source, field, value)
                created_raw_ids = (
                    set(
                        (
                            await db.scalars(
                                select(RawIngestion.id).where(RawIngestion.source_id == source_id)
                            )
                        ).all()
                    )
                    - original_raw_ids
                )
                created_source_audit_ids = (
                    set(
                        (
                            await db.scalars(
                                select(AuditEvent.id).where(
                                    AuditEvent.resource_id == str(source_id)
                                )
                            )
                        ).all()
                    )
                    - original_source_audit_ids
                )
                await db.execute(
                    delete(InstrumentIdentifier).where(
                        InstrumentIdentifier.instrument_id.in_(instrument_ids)
                    )
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(created_raw_ids)))
                await db.execute(delete(Instrument).where(Instrument.id.in_(instrument_ids)))
                await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id == user_id))
                await db.execute(
                    delete(AuditEvent).where(AuditEvent.id.in_(created_source_audit_ids))
                )
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
                await get_engine().dispose()

    asyncio.run(run())
