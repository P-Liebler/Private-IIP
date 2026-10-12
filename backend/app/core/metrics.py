"""Small Prometheus exposition for the single-process V1 API."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select

from app.core.valkey import make_valkey_client
from app.db.session import check_database, get_session_factory
from app.models import DataQuarantine, PriceDaily, RawIngestion

router = APIRouter()
_request_count: Counter[tuple[str, str, int]] = Counter()
_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
_valuation_failures = 0
BACKUP_STATUS_PATH = Path("/app/runtime/backup-status.json")


def observe(method: str, route: str, status: int, duration: float) -> None:
    global _valuation_failures
    key = (method, route, status)
    _request_count[key] += 1
    _duration_sum[(method, route)] += duration
    if route.endswith("/valuation") and status >= 500:
        _valuation_failures += 1


@router.get("/internal/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    lines = [
        "# TYPE private_iip_http_requests_total counter",
        "# TYPE private_iip_http_duration_seconds_sum counter",
        "# TYPE private_iip_db_ready gauge",
        "# TYPE private_iip_failed_imports gauge",
        "# TYPE private_iip_quarantined_rows gauge",
        "# TYPE private_iip_stale_prices gauge",
        "# TYPE private_iip_valuation_failures_total counter",
        "# TYPE private_iip_backup_success gauge",
        "# TYPE private_iip_backup_timestamp_seconds gauge",
        "# TYPE private_iip_queue_depth gauge",
        "# TYPE private_iip_queue_ready gauge",
    ]
    for (method, route, status), count in sorted(_request_count.items()):
        safe_route = route.replace('"', "").replace("\\", "")
        labels = f'method="{method}",route="{safe_route}",status="{status}"'
        lines.append(f"private_iip_http_requests_total{{{labels}}} {count}")
    for (method, route), duration in sorted(_duration_sum.items()):
        safe_route = route.replace('"', "").replace("\\", "")
        labels = f'method="{method}",route="{safe_route}"'
        lines.append(f"private_iip_http_duration_seconds_sum{{{labels}}} {duration:.6f}")
    try:
        await check_database()
        lines.append("private_iip_db_ready 1")
        async with get_session_factory()() as db:
            failed = await db.scalar(
                select(func.count())
                .select_from(RawIngestion)
                .where(RawIngestion.status == "FAILED")
            )
            quarantined = await db.scalar(select(func.count()).select_from(DataQuarantine))
            latest = (
                select(
                    PriceDaily.instrument_id, func.max(PriceDaily.trading_date).label("last_date")
                )
                .group_by(PriceDaily.instrument_id)
                .subquery()
            )
            stale = await db.scalar(
                select(func.count())
                .select_from(latest)
                .where(latest.c.last_date < datetime.now(UTC).date() - timedelta(days=7))
            )
            lines.extend(
                [
                    f"private_iip_failed_imports {failed or 0}",
                    f"private_iip_quarantined_rows {quarantined or 0}",
                    f"private_iip_stale_prices {stale or 0}",
                ]
            )
    except Exception:
        lines.append("private_iip_db_ready 0")
    lines.append(f"private_iip_valuation_failures_total {_valuation_failures}")
    valkey = make_valkey_client()
    try:
        depth = await cast(Awaitable[int], valkey.llen("celery"))
        lines.extend(["private_iip_queue_ready 1", f"private_iip_queue_depth {depth}"])
    except Exception:
        lines.append("private_iip_queue_ready 0")
    finally:
        await valkey.aclose()
    if BACKUP_STATUS_PATH.exists():
        try:
            status = json.loads(BACKUP_STATUS_PATH.read_text(encoding="utf-8"))
            lines.append(f"private_iip_backup_success {1 if status['success'] else 0}")
            lines.append(
                f"private_iip_backup_timestamp_seconds {int(status['completed_timestamp'])}"
            )
        except (OSError, ValueError, KeyError, TypeError):
            lines.append("private_iip_backup_success 0")
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
