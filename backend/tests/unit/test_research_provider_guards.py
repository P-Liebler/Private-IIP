from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataSource
from app.providers.company_ir import CompanyIRCollector, ReportContract
from app.providers.news_rss import RssCollector
from app.providers.sec import check_sec_rate


def test_sec_valkey_failure_cannot_bypass_global_limit() -> None:
    async def run() -> None:
        client = MagicMock()
        client.eval = AsyncMock(side_effect=RedisError("test unavailable"))
        client.aclose = AsyncMock()
        with (
            patch("app.providers.sec.check_provider_rate", new=AsyncMock()),
            patch("app.providers.sec.make_valkey_client", return_value=client),
        ):
            with pytest.raises(AppError) as error:
                await check_sec_rate(DataSource(slug="SEC_EDGAR", rate_limit_per_minute=600))
            assert error.value.code == "SOURCE_RATE_UNAVAILABLE"
            client.aclose.assert_awaited_once()

    asyncio.run(run())


def test_ir_and_rss_unknown_sources_do_not_resolve_dns_or_http() -> None:
    async def run() -> None:
        source = DataSource(slug="TEST_BLOCKED", gate_status="UNKNOWN", enabled=False)
        with (
            patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
            patch("app.providers.company_ir.validate_public_endpoint", new=AsyncMock()) as dns,
            patch("app.providers.news_rss.validate_public_endpoint", new=AsyncMock()) as rss_dns,
        ):
            http = MagicMock()
            http.get = AsyncMock()
            db = MagicMock(spec=AsyncSession)
            from uuid import uuid4

            with pytest.raises(AppError):
                await CompanyIRCollector(db, client=http).collect(
                    ReportContract(
                        instrument_id=uuid4(),
                        url="https://example.org/report.csv",
                        approved_host="example.org",
                    )
                )
            with pytest.raises(AppError):
                await RssCollector(db, client=http).collect(
                    "https://example.org/rss", "example.org"
                )
            http.get.assert_not_awaited()
            dns.assert_not_awaited()
            rss_dns.assert_not_awaited()

    asyncio.run(run())
