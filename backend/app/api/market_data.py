from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.db.session import get_session
from app.providers.ecb_fx import EcbFxCollector
from app.services.auth import AuthContext
from app.services.market_import import MarketImportService
from app.services.market_queries import MarketQueryService, total_return

router = APIRouter(prefix="/api/v1", tags=["market-data"])


class ImportCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_ingestion_id: UUID
    mapping: dict[str, str]
    accept_partial: bool = False
    conflict_policy: Literal["REJECT", "ACCEPT_NEW", "KEEP_EXISTING"] = "REJECT"
    decision_note: str | None = Field(default=None, max_length=180)


class CollectRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date
    end: date


@router.post("/market-data/imports/{kind}/preview")
async def preview_market(
    kind: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> dict[str, object]:
    if request.headers.get("Content-Type", "").split(";", 1)[0].lower() != "text/csv":
        raise AppError(415, "CSV_CONTENT_TYPE_REQUIRED", "Upload a text/csv file")
    filename = request.headers.get("X-Filename", "upload.csv")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV exceeds 5 MB")
    try:
        return await MarketImportService(db).preview(kind, bytes(data), filename, _context.user.id)
    except ValueError as error:
        raise AppError(422, "CSV_METADATA_INVALID", str(error)) from error


@router.post("/market-data/imports/{kind}/commit")
async def commit_market(
    kind: str,
    payload: ImportCommit,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> dict[str, object]:
    return await MarketImportService(db).commit(
        kind,
        payload.raw_ingestion_id,
        payload.mapping,
        accept_partial=payload.accept_partial,
        conflict_policy=payload.conflict_policy,
        decision_note=payload.decision_note,
        actor_user_id=context.user.id,
    )


@router.get("/instruments/{instrument_id}/prices")
async def prices(
    instrument_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
    start: date | None = None,
    end: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, object]:
    last = end or datetime.now(UTC).date()
    first = start or last - timedelta(days=365)
    return await MarketQueryService(db).prices(instrument_id, first, last, as_of)


@router.get("/instruments/{instrument_id}/prices/{trading_date}/versions")
async def price_versions(
    instrument_id: UUID,
    trading_date: date,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> list[dict[str, object]]:
    return await MarketQueryService(db).price_versions(instrument_id, trading_date)


@router.get("/instruments/{instrument_id}/corporate-actions")
async def corporate_actions(
    instrument_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
    start: date | None = None,
    end: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, object]:
    last = end or datetime.now(UTC).date()
    first = start or last - timedelta(days=3650)
    return await MarketQueryService(db).actions(instrument_id, first, last, as_of)


@router.get("/instruments/{instrument_id}/return")
async def instrument_return(
    instrument_id: UUID,
    start: date,
    end: date,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
    as_of: datetime | None = None,
) -> dict[str, object]:
    query = MarketQueryService(db)
    prices_result = await query.prices(instrument_id, start, end, as_of)
    prices_list = cast(list[dict[str, object]], prices_result["prices"])
    if len(prices_list) < 2:
        return {"status": "UNAVAILABLE", "reason": "NEED_TWO_VERIFIED_CLOSES"}
    actions_result = await query.actions(instrument_id, start, end, as_of)
    first, last = prices_list[0], prices_list[-1]
    actions = [
        action
        for action in cast(list[dict[str, object]], actions_result["actions"])
        if cast(date, first["date"]) < cast(date, action["date"]) <= cast(date, last["date"])
    ]
    if any(action["type"] in {"TICKER_CHANGE", "DELISTING"} for action in actions):
        return {"status": "UNAVAILABLE", "reason": "ACTION_REQUIRES_REVIEW"}
    return {
        "status": "PROVISIONAL",
        "action_coverage": "UNVERIFIED",
        "start": first["date"],
        "end": last["date"],
        "total_return": total_return(
            cast(Decimal, first["close"]), cast(Decimal, last["close"]), actions
        ),
        "policy": "raw-close-explicit-actions-v1",
        "price_version_ids": [first["id"], last["id"]],
        "action_version_ids": [action["id"] for action in actions],
    }


@router.get("/fx/rate")
async def fx_rate(
    base: Annotated[str, Query(min_length=3, max_length=3)],
    quote: Annotated[str, Query(min_length=3, max_length=3)],
    on_date: date,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
    as_of: datetime | None = None,
) -> dict[str, object]:
    return await MarketQueryService(db).fx(base, quote, on_date, as_of)


@router.post("/fx/providers/ecb/collect")
async def collect_ecb_fx(
    payload: CollectRange,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> dict[str, object]:
    require_data_operator(_context.user)
    return await EcbFxCollector(db).collect(payload.start, payload.end)


@router.get("/data-quality/summary")
async def quality_summary(
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> dict[str, object]:
    return await MarketQueryService(db).quality_summary()
