from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.models import DataSource, Filing, FundamentalFact, Instrument, RawIngestion
from app.providers.sec import SecCollector, check_sec_rate
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceService
from tests.integration.test_market_foundation import MemoryStorage


@pytest.mark.integration
@pytest.mark.parametrize("scenario", ["success", "invalid", "empty", "429", "503", "timeout"])
def test_sec_archives_every_response_before_parse(scenario: str) -> None:
    async def run() -> None:
        settings = get_settings()
        previous = (settings.sec_enabled, settings.sec_user_agent, settings.sec_contact_email)
        settings.sec_enabled = True
        settings.sec_user_agent = "Synthetic local collector test"
        settings.sec_contact_email = "fixture@example.org"
        async with get_session_factory()() as db:
            source = DataSource(
                id=uuid4(),
                slug=f"TEST_SEC_{uuid4().hex}",
                name="Synthetic SEC",
                type="OFFICIAL",
                trust_level="A",
                priority=20,
                gate_status="APPROVED",
                enabled=True,
                checked_at=datetime.now(UTC),
                terms_url="https://www.sec.gov/about/developer-resources",
                scope="test fixture only",
                decision_by="test",
                next_review_at=datetime.now(UTC) + timedelta(days=1),
                allowed_uses=["fundamentals", "filings"],
                failure_count=0,
            )
            instrument = Instrument(
                id=uuid4(),
                ticker="P5TEST",
                name="Synthetic SEC company",
                asset_type="STOCK",
                country="US",
                currency="USD",
            )
            db.add_all([source, instrument])
            await db.commit()
            sid, iid = source.id, instrument.id
            storage = MemoryStorage()
            raw = RawIngestionService(db, storage)
            calls = 0

            def transport(request: httpx.Request) -> httpx.Response:
                nonlocal calls
                calls += 1
                if scenario == "timeout":
                    raise httpx.ReadTimeout("synthetic timeout", request=request)
                if scenario in {"429", "503"}:
                    return httpx.Response(
                        int(scenario),
                        content=b"synthetic unavailable",
                        headers={"Retry-After": "0"},
                    )
                if scenario == "empty":
                    return httpx.Response(200, content=b"")
                if scenario == "invalid":
                    return httpx.Response(200, content=b"invalid-json")
                if request.url.path.startswith("/Archives/"):
                    return httpx.Response(
                        200,
                        content=b"<html>SYNTHETIC PRIMARY FILING</html>",
                        headers={"Content-Type": "text/html"},
                    )
                directory = Path(__file__).parents[1] / "fixtures" / "sec"
                file = (
                    "synthetic_companyfacts.json"
                    if "companyfacts" in request.url.path
                    else "synthetic_submissions.json"
                )
                return httpx.Response(
                    200,
                    content=(directory / file).read_bytes(),
                    headers={"Content-Type": "application/json"},
                )

            async def lookup(_service: SourceService, _slug: str) -> DataSource:
                return source

            try:
                with (
                    patch.object(SourceService, "get", lookup),
                    patch("app.providers.sec.asyncio.sleep", new=AsyncMock()),
                ):
                    async with httpx.AsyncClient(
                        transport=httpx.MockTransport(transport)
                    ) as client:
                        collector = SecCollector(db, raw, client, AsyncMock())
                        if scenario == "success":
                            result = await collector.collect(iid, "1")
                            assert result["inserted"] == 9
                            filing = await db.scalar(
                                select(Filing)
                                .where(Filing.instrument_id == iid)
                                .order_by(Filing.known_at)
                                .limit(1)
                            )
                            assert filing is not None and filing.document_hash is None
                            downloaded = await collector.download_filing(filing.id)
                            assert downloaded.document_hash == downloaded.response_hash
                            assert await raw.get_verified(downloaded.raw_ingestion_id) == (
                                b"<html>SYNTHETIC PRIMARY FILING</html>"
                            )
                            facts = (
                                await db.scalars(
                                    select(FundamentalFact).where(
                                        FundamentalFact.instrument_id == iid
                                    )
                                )
                            ).all()
                            revenues = sorted(
                                [
                                    f
                                    for f in facts
                                    if f.metric == "revenue" and f.period_type == "ANNUAL"
                                ],
                                key=lambda f: f.known_at,
                            )
                            assert [f.value for f in revenues] == [1000, 950]
                            assert revenues[1].replaces_version_id == revenues[0].id
                        else:
                            with pytest.raises(AppError):
                                await collector.collect(iid, "1")
                        rows = (
                            await db.scalars(
                                select(RawIngestion).where(RawIngestion.source_id == sid)
                            )
                        ).all()
                        assert len(rows) == calls and 1 <= calls <= 3
                        for row in rows:
                            if scenario == "timeout":
                                assert row.status == "FAILED" and row.object_path is None
                            else:
                                assert (
                                    await raw.get_verified(row.id)
                                    == storage.objects[row.object_path]
                                )
            finally:
                await db.rollback()
                for model in [FundamentalFact, Filing, RawIngestion]:
                    await db.execute(delete(model).where(model.source_id == sid))
                await db.execute(delete(Instrument).where(Instrument.id == iid))
                await db.execute(delete(DataSource).where(DataSource.id == sid))
                await db.commit()
                settings.sec_enabled, settings.sec_user_agent, settings.sec_contact_email = previous
        await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_sec_rate_is_global_across_concurrent_workers() -> None:
    async def run() -> None:
        await asyncio.sleep(1.05)
        sources = [
            DataSource(slug=f"TEST_RATE_{uuid4().hex}", rate_limit_per_minute=600)
            for _ in range(12)
        ]
        results = await asyncio.gather(
            *(check_sec_rate(source) for source in sources), return_exceptions=True
        )
        assert sum(result is None for result in results) == get_settings().sec_rate_limit
        assert all(
            result is None or isinstance(result, AppError) and result.code == "SOURCE_RATE_LIMITED"
            for result in results
        )

    asyncio.run(run())
