from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session_factory
from app.jobs.celery_app import celery_app
from app.providers.company_ir import CompanyIRCollector, ReportContract
from app.providers.news_rss import RssCollector
from app.providers.sec import SecCollector
from app.repositories.core import delete_old_sessions
from app.services.research import ResearchService
from app.services.sources import SourceGate, SourceService


@celery_app.task(name="system.ping")  # type: ignore[misc]
def system_ping() -> dict[str, str]:
    return {"status": "ok", "executed_at": datetime.now(UTC).isoformat()}


@celery_app.task(name="research.collect_approved")  # type: ignore[misc]
def collect_approved_research() -> dict[str, int]:
    async def run() -> dict[str, int]:
        result = {"collected": 0, "skipped": 0, "failed": 0}
        contracts = json.loads(get_settings().research_collection_contracts)
        async with get_session_factory()() as db:
            for contract in contracts:
                slug = contract.get(
                    "source_slug",
                    "SEC_EDGAR"
                    if contract["kind"] == "sec"
                    else "COMPANY_IR"
                    if contract["kind"] == "ir"
                    else "NEWS_RSS",
                )
                try:
                    source = await SourceService(db).get(slug)
                    SourceGate.require_enabled(
                        source, "news" if contract["kind"] == "rss" else "fundamentals"
                    )
                except AppError:
                    result["skipped"] += 1
                    continue
                try:
                    if contract["kind"] == "sec":
                        identifier = UUID(contract["instrument_id"])
                        await SecCollector(db).collect(identifier, contract["cik"])
                        await ResearchService(db).materialize(identifier)
                    elif contract["kind"] == "ir":
                        report = ReportContract.model_validate(
                            {k: v for k, v in contract.items() if k != "kind"}
                        )
                        await CompanyIRCollector(db).collect(report)
                        await ResearchService(db).materialize(report.instrument_id)
                    elif contract["kind"] == "rss":
                        await RssCollector(db).collect(
                            contract["url"], contract["approved_host"], slug
                        )
                    else:
                        raise ValueError("Unknown collection type")
                    result["collected"] += 1
                except Exception:
                    await db.rollback()
                    source = await SourceService(db).get(slug)
                    source.last_failure = datetime.now(UTC)
                    source.failure_count += 1
                    await db.commit()
                    result["failed"] += 1
        return result

    return asyncio.run(run())


@celery_app.task(name="auth.cleanup_sessions")  # type: ignore[misc]
def cleanup_sessions() -> dict[str, int]:
    async def run() -> int:
        async with get_session_factory()() as db:
            removed = await delete_old_sessions(db, older_than=datetime.now(UTC))
            await db.commit()
            return removed

    return {"removed": asyncio.run(run())}
