from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.storage import get_storage
from app.core.valkey import check_valkey
from app.db.session import check_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    services: dict[str, Literal["ok", "unavailable"]]


async def _probe(name: str, check: Callable[[], Awaitable[None]]) -> tuple[str, str]:
    try:
        await asyncio.wait_for(check(), timeout=4)
        return name, "ok"
    except Exception as error:
        logger.warning("health probe %s failed: %s", name, type(error).__name__)
        return name, "unavailable"


async def _check_minio() -> None:
    # This also creates the empty development bucket automatically on first startup.
    await asyncio.to_thread(get_storage().ensure_bucket)


async def probe_services() -> dict[str, str]:
    result = await asyncio.gather(
        _probe("database", check_database),
        _probe("valkey", check_valkey),
        _probe("minio", _check_minio),
    )
    return dict(result)


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok", services={})


async def _readiness_response(services: dict[str, str]) -> JSONResponse:
    status = "ok" if all(value == "ok" for value in services.values()) else "degraded"
    return JSONResponse(
        status_code=200 if status == "ok" else 503, content={"status": status, "services": services}
    )


@router.get("", response_model=HealthResponse)
async def health(services: Annotated[dict[str, str], Depends(probe_services)]) -> JSONResponse:
    return await _readiness_response(services)


@router.get("/ready", response_model=HealthResponse)
async def ready(services: Annotated[dict[str, str], Depends(probe_services)]) -> JSONResponse:
    return await _readiness_response(services)
