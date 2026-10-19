"""Authenticated operational status without backup paths or secrets."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from redis.exceptions import RedisError

from app.api.dependencies import require_user
from app.api.health import probe_services
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.services.auth import AuthContext

router = APIRouter(prefix="/api/v1/system", tags=["system"])
RUNTIME = Path("/app/runtime")


def _status(name: str) -> dict[str, object]:
    try:
        value = json.loads((RUNTIME / name).read_text(encoding="utf-8"))
        if not isinstance(value["success"], bool):
            raise ValueError("Invalid operational outcome")
        stamp = datetime.fromisoformat(value["completed_at"])
        if stamp.tzinfo is None or stamp > datetime.now(UTC):
            raise ValueError("Invalid operational timestamp")
        return {
            "status": "SUCCESS" if value["success"] else "FAILED",
            "completed_at": value.get("completed_at"),
            "run_id": value.get("run_id", value.get("backup_run_id")),
            "age_seconds": int((datetime.now(UTC) - stamp).total_seconds()),
        }
    except (OSError, ValueError, KeyError, TypeError, RedisError):
        return {"status": "UNAVAILABLE", "completed_at": None, "run_id": None}


@router.get("/backup-status")
async def backup_status(_user: Annotated[AuthContext, Depends(require_user)]) -> dict[str, object]:
    return {"backup": _status("backup-status.json"), "restore_test": _status("restore-status.json")}


async def require_operations_operator(
    context: Annotated[AuthContext, Depends(require_user)],
) -> AuthContext:
    if context.user.username not in get_settings().operations_operator_usernames:
        raise AppError(403, "OPERATIONS_OPERATOR_REQUIRED", "Operations access required")
    return context


async def optional_service(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            response = await client.get(url)
        return "HEALTHY" if response.status_code == 200 else "UNAVAILABLE"
    except httpx.HTTPError:
        return "UNAVAILABLE"


async def scheduler_status() -> str:
    client = make_valkey_client()
    try:
        raw = await client.get("intelligence:last-dispatch")
        if raw:
            age = datetime.now(UTC).timestamp() - float(json.loads(raw)["completed_at"])
            if 0 <= age < 180:
                return "HEALTHY"
        return "DEGRADED"
    except (OSError, ValueError, KeyError, TypeError):
        return "UNAVAILABLE"
    finally:
        await client.aclose()


async def worker_status() -> str:
    from app.jobs.celery_app import celery_app

    try:
        result = await asyncio.to_thread(celery_app.control.ping, timeout=1.0)
        return "HEALTHY" if result else "UNAVAILABLE"
    except Exception:
        return "UNAVAILABLE"


@router.get("/status")
async def system_status(
    _operator: Annotated[AuthContext, Depends(require_operations_operator)],
) -> dict[str, object]:
    settings = get_settings()
    core, worker, scheduler, mlflow, ollama = await asyncio.gather(
        probe_services(),
        worker_status(),
        scheduler_status(),
        optional_service(settings.mlflow_tracking_uri + "/health"),
        optional_service(settings.ollama_base_url + "/api/version"),
    )
    services = {key: "HEALTHY" if value == "ok" else "UNAVAILABLE" for key, value in core.items()}
    services.update(worker=worker, scheduler=scheduler, mlflow=mlflow, ollama=ollama)
    return {
        "application_version": "0.1.0",
        "code_commit": settings.code_commit,
        "environment": settings.app_env,
        "status": "HEALTHY"
        if all(value == "HEALTHY" for value in services.values())
        else "DEGRADED",
        "services": services,
        "backup": _status("backup-status.json"),
        "last_successful_backup": _status("last-successful-backup.json"),
        "restore_test": _status("restore-status.json"),
        "data_collection_enabled": settings.data_collection_enabled,
        "forward_shadow_enabled": settings.forward_shadow_enabled,
        "data_quality": "SEE_DATA_QUALITY_AND_REAL_READINESS",
        "decisions": {
            "core": "PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED",
            "real_data": "REAL_DATA_LIMITED",
            "forecasts": "FORECASTS_SHADOW_ONLY",
            "recommendations": "RECOMMENDATIONS_GATED",
        },
        "operator_evidence": {
            key: "NOT_VERIFIED"
            for key in (
                "target_host",
                "vpn_access",
                "tls_client_trust",
                "independent_backup",
                "daily_backup_schedule",
                "secret_recovery",
                "alert_delivery",
            )
        },
    }
