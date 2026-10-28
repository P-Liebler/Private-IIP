from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AnalystEstimate,
    AuditEvent,
    DataSource,
    Filing,
    FundamentalFact,
    Instrument,
    NewsArticle,
    NewsInstrument,
    RawIngestion,
    ResearchMetric,
    ResearchSnapshot,
    User,
    Watchlist,
    WatchlistItem,
)
from app.providers.sec import SecCollector, parse_companyfacts, parse_submissions
from app.schemas.research import EstimateInput, FactInput
from app.services.analyst_estimates import EstimateService
from app.services.auth import AuthService
from app.services.fundamentals import FundamentalService
from app.services.news import NewsInput, NewsService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceService
from tests.integration.test_market_foundation import MemoryStorage


@pytest.mark.integration
def test_pit_restatement_and_research_api_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> None:
        factory = get_session_factory()
        async with factory() as db:
            source = DataSource(
                id=uuid4(),
                slug=f"TEST_P5_{uuid4().hex}",
                name="Synthetic P5 source",
                type="MANUAL",
                trust_level="D",
                priority=10,
                gate_status="APPROVED",
                enabled=True,
                checked_at=datetime.now(UTC),
                allowed_uses=["fundamentals", "news", "estimates"],
                failure_count=0,
            )
            instrument = Instrument(
                id=uuid4(),
                name="Synthetic P5 US",
                ticker="P5TEST",
                asset_type="STOCK",
                currency="USD",
                country="US",
            )
            swiss = Instrument(
                id=uuid4(),
                name=f"Synthetic P5 CH {uuid4().hex}",
                asset_type="STOCK",
                currency="CHF",
                country="CH",
            )
            db.add_all([source, instrument, swiss])
            await db.commit()
            user = await AuthService(db).create_user(
                "p5_" + uuid4().hex[:12], "test-only-p5-password-2"
            )
            other = await AuthService(db).create_user(
                "p5_" + uuid4().hex[:12], "test-only-p5-password-2"
            )
            storage = MemoryStorage()
            raw_service = RawIngestionService(db, storage)
            original_get = SourceService.get

            async def test_get(
                service: SourceService, slug: str, *, lock: bool = False
            ) -> DataSource:
                if slug == "MANUAL_RESEARCH":
                    row = await service.db.get(DataSource, source.id)
                    assert row is not None
                    return row
                return await original_get(service, slug, lock=lock)

            monkeypatch.setattr(SourceService, "get", test_get)
            try:
                raw = await raw_service.store(
                    data=b"SYNTHETIC ORIGINAL REPORT",
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="synthetic_test_report",
                )
                # Explicit synthetic logical acquisition clock for a historical archive test.
                raw.received_at = datetime(2026, 3, 1, 13, tzinfo=UTC)
                await db.commit()
                original = FactInput(
                    instrument_id=instrument.id,
                    metric="revenue",
                    value="1000",
                    unit="MONEY",
                    currency="USD",
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    period_type="ANNUAL",
                    filing_reference="SYNTHETIC-ORIGINAL",
                    known_at=datetime(2026, 3, 1, 12, tzinfo=UTC),
                    availability_evidence="Synthetic test release",
                )
                service = FundamentalService(db, raw_service)
                await service.persist([original], raw, parser="synthetic-test-v1")
                await db.commit()
                assert not await service.get_fundamentals(
                    instrument.id, datetime(2026, 3, 1, 12, 30, tzinfo=UTC)
                )
                assert (
                    await service.get_fundamentals(instrument.id, datetime(2026, 4, 1, tzinfo=UTC))
                )[0].value == 1000
                correction = await raw_service.store(
                    data=b"SYNTHETIC AMENDED REPORT",
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="synthetic_test_report",
                )
                correction.received_at = datetime(2026, 5, 1, 13, tzinfo=UTC)
                await db.commit()
                changed = original.model_copy(
                    update={
                        "value": Decimal(950),
                        "filing_reference": "SYNTHETIC-AMENDED",
                        "known_at": datetime(2026, 5, 1, 12, tzinfo=UTC),
                    }
                )
                await service.persist([changed], correction, parser="synthetic-test-v1")
                await db.commit()
                assert (
                    await service.get_fundamentals(instrument.id, datetime(2026, 4, 1, tzinfo=UTC))
                )[0].value == 1000
                latest = (
                    await service.get_fundamentals(instrument.id, datetime(2026, 6, 1, tzinfo=UTC))
                )[0]
                assert latest.value == 950 and latest.replaces_version_id
                assert (await service.persist([changed], correction, parser="synthetic-test-v1"))[
                    "unchanged"
                ] == 1
                await db.commit()
                csv = (
                    "instrument_id,metric,value,unit,currency,period_start,period_end,"
                    "period_type,filing_reference\n"
                    f"{swiss.id},revenue,2000,MONEY,CHF,2025-01-01,2025-12-31,"
                    "ANNUAL,SYNTHETIC-CH\n"
                ).encode()
                preview = await service.upload(csv, "synthetic.csv", user.id)
                assert preview["can_commit"]
                await service.commit(preview["raw_ingestion_id"], {}, user.id)
                assert not await service.get_fundamentals(
                    swiss.id, datetime(2026, 9, 1, tzinfo=UTC)
                )
                with pytest.raises(AppError):
                    await service.preview(preview["raw_ingestion_id"], {}, other.id)
                assert await raw_service.get_verified(preview["raw_ingestion_id"]) == csv
                estimate_raw = await raw_service.store(
                    data=b"SYNTHETIC ESTIMATE SNAPSHOT",
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="manual_estimates",
                )
                estimate = EstimateInput(
                    instrument_id=instrument.id,
                    estimate_type="EPS",
                    target_period=date(2026, 12, 31),
                    value="12",
                    unit="PER_SHARE",
                    currency="USD",
                )
                assert await EstimateService(db).persist([estimate], estimate_raw) == 1
                assert await EstimateService(db).persist([estimate], estimate_raw) == 0
                assert not await EstimateService(db).history(
                    instrument.id, estimate_raw.received_at - timedelta(seconds=1)
                )
                news_raw = await raw_service.store(
                    data=b"SYNTHETIC NEWS METADATA",
                    source_id=source.id,
                    source_slug=source.slug,
                    resource_type="manual_news",
                )
                item = NewsInput(
                    title=f"Synthetic company publishes annual results {news_raw.id}",
                    source_url=f"https://example.org/{news_raw.id}?utm_source=feed",
                    published_at=datetime(2026, 3, 1, tzinfo=UTC),
                    identifiers=[],
                )
                result = await NewsService(db).persist(
                    [
                        item,
                        item.model_copy(
                            update={"source_url": f"https://example.org/{news_raw.id}"}
                        ),
                    ],
                    news_raw,
                )
                assert result == {"inserted": 2, "duplicates": 1}
                assert not await NewsService(db).list(
                    as_of=datetime(2026, 4, 1, tzinfo=UTC), source_id=source.id
                )
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
                ) as client:
                    assert (await client.get("/api/v1/research/instruments")).status_code == 401
                    login = await client.post(
                        "/api/v1/auth/login",
                        json={"username": user.username, "password": "test-only-p5-password-2"},
                    )
                    assert login.status_code == 200
                    response = await client.get(
                        f"/api/v1/research/instruments/{instrument.id}?as_of=2026-04-01T00:00:00Z"
                    )
                    assert response.status_code == 200, response.text
                    assert response.json()["facts"][0]["value"] == "1000.000000000000"
                    assert response.json()["scores"]["Quality"]["score"] is None
                    refresh = await client.post(f"/api/v1/research/instruments/{swiss.id}/refresh")
                    assert refresh.status_code == 200, refresh.text
                    screen = await client.get(
                        "/api/v1/research/instruments",
                        params={"country": "CH", "q": swiss.name, "limit": 10},
                    )
                    assert screen.status_code == 200, screen.text
                    assert any(
                        row["instrument"]["id"] == str(swiss.id) for row in screen.json()["items"]
                    )
                    watch = await client.post(
                        "/api/v1/watchlists", json={"name": "Synthetic Watchlist"}
                    )
                    assert watch.status_code == 201, watch.text
                    identifier = watch.json()["id"]
                    for _ in range(2):
                        added = await client.put(
                            f"/api/v1/watchlists/{identifier}/items",
                            json={
                                "instrument_id": str(swiss.id),
                                "notes": "private test note",
                                "tags": ["CH"],
                            },
                        )
                        assert added.status_code == 200, added.text
                    assert (
                        len((await client.get(f"/api/v1/watchlists/{identifier}/items")).json())
                        == 1
                    )
                    renamed = await client.patch(
                        f"/api/v1/watchlists/{identifier}", json={"name": "Renamed"}
                    )
                    assert renamed.status_code == 200
                    await client.post("/api/v1/auth/logout")
                    await client.post(
                        "/api/v1/auth/login",
                        json={"username": other.username, "password": "test-only-p5-password-2"},
                    )
                    assert (
                        await client.get(f"/api/v1/watchlists/{identifier}/items")
                    ).status_code == 404
                    assert (
                        await client.put(
                            f"/api/v1/watchlists/{identifier}/items",
                            json={"instrument_id": str(swiss.id)},
                        )
                    ).status_code == 404
                    quality = await client.get("/api/v1/data-quality/research")
                    assert quality.status_code == 200, quality.text
            finally:
                await db.rollback()
                for row in (user, other, source, instrument, swiss):
                    await db.refresh(row)
                for model in [WatchlistItem, Watchlist]:
                    query = (
                        delete(model).where(
                            model.watchlist_id.in_(
                                select(Watchlist.id).where(
                                    Watchlist.user_id.in_([user.id, other.id])
                                )
                            )
                        )
                        if model is WatchlistItem
                        else delete(model).where(model.user_id.in_([user.id, other.id]))
                    )
                    await db.execute(query)
                snapshot_ids = select(ResearchSnapshot.id).where(
                    ResearchSnapshot.instrument_id.in_([instrument.id, swiss.id])
                )
                await db.execute(
                    delete(ResearchMetric).where(ResearchMetric.snapshot_id.in_(snapshot_ids))
                )
                await db.execute(
                    delete(ResearchSnapshot).where(
                        ResearchSnapshot.instrument_id.in_([instrument.id, swiss.id])
                    )
                )
                await db.execute(
                    delete(NewsInstrument).where(
                        NewsInstrument.article_id.in_(
                            select(NewsArticle.id).where(NewsArticle.source_id == source.id)
                        )
                    )
                )
                for model in [NewsArticle, AnalystEstimate, FundamentalFact, Filing, RawIngestion]:
                    await db.execute(delete(model).where(model.source_id == source.id))
                await db.execute(
                    delete(Instrument).where(Instrument.id.in_([instrument.id, swiss.id]))
                )
                await db.execute(
                    delete(AuditEvent).where(AuditEvent.actor_user_id.in_([user.id, other.id]))
                )
                await db.execute(delete(User).where(User.id.in_([user.id, other.id])))
                await db.execute(delete(DataSource).where(DataSource.id == source.id))
                await db.commit()
        await get_engine().dispose()

    asyncio.run(run())


def test_sec_saved_fixtures_amendment_and_quarterly() -> None:
    directory = Path(__file__).parents[1] / "fixtures" / "sec"
    rows = parse_submissions((directory / "synthetic_submissions.json").read_bytes(), "0000000001")
    filings = {row["accession_number"]: Filing(id=uuid4(), **row) for row in rows}
    inputs, warnings = parse_companyfacts(
        (directory / "synthetic_companyfacts.json").read_bytes(), "0000000001", uuid4(), filings
    )
    assert not warnings
    assert [f.value for f in inputs if f.metric == "revenue"] == [1000, 250, 950]
    assert any(f.period_type == "QUARTER" for f in inputs)


@pytest.mark.integration
@pytest.mark.parametrize("state", ["UNKNOWN", "BLOCKED", "EXPIRED", "DISABLED"])
def test_sec_gate_zero_network(state: str) -> None:
    async def run() -> None:
        calls = 0

        def http(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={})

        async with get_session_factory()() as db:
            source = DataSource(
                id=uuid4(),
                slug=f"TEST_SEC_{uuid4().hex}",
                name="Test only SEC",
                type="OFFICIAL",
                trust_level="A",
                priority=10,
                gate_status="APPROVED" if state in {"EXPIRED", "DISABLED"} else state,
                enabled=state == "EXPIRED",
                checked_at=datetime.now(UTC),
                terms_url="https://www.sec.gov/about/developer-resources",
                scope="test",
                decision_by="test",
                next_review_at=datetime.now(UTC) - timedelta(days=1),
                allowed_uses=["fundamentals"],
                failure_count=0,
            )
            db.add(source)
            await db.commit()

            async def lookup(_service: SourceService, _slug: str) -> DataSource:
                return source

            from unittest.mock import patch

            try:
                with patch.object(SourceService, "get", lookup):
                    async with httpx.AsyncClient(transport=httpx.MockTransport(http)) as client:
                        with pytest.raises(AppError) as error:
                            await SecCollector(db, client=client, limiter=AsyncMock()).fetch(
                                "/submissions/CIK0000000001.json", uuid4()
                            )
                        assert error.value.code == "SOURCE_NOT_APPROVED"
                assert calls == 0
            finally:
                await db.execute(delete(DataSource).where(DataSource.id == source.id))
                await db.commit()
        await get_engine().dispose()

    asyncio.run(run())
