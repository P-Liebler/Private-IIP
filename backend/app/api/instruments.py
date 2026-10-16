from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.db.session import get_session
from app.providers.openfigi import MappingService, OpenFigiProvider
from app.schemas.instruments import (
    IdentifierResponse,
    IdentifierUpdate,
    InstrumentCreate,
    InstrumentDetailResponse,
    InstrumentResponse,
    InstrumentSearchResult,
    InstrumentUpdate,
)
from app.services.auth import AuthContext
from app.services.instruments import InstrumentService

router = APIRouter(prefix="/api/v1/instruments", tags=["instruments"])


class MappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(pattern=r"^(TICKER|ISIN|FIGI)$")
    value: str = Field(min_length=1, max_length=40)


class MappingAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_ingestion_id: UUID
    figi: str = Field(min_length=12, max_length=12)


@router.get("/search", response_model=list[InstrumentSearchResult])
async def search(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> list[InstrumentSearchResult]:
    return [InstrumentSearchResult.from_hit(hit) for hit in await InstrumentService(db).search(q)]


@router.post("", response_model=InstrumentResponse, status_code=201)
async def create(
    payload: InstrumentCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> InstrumentResponse:
    try:
        instrument = await InstrumentService(db).create(
            **payload.model_dump(),
            actor_user_id=context.user.id,
        )
    except ValueError as error:
        raise AppError(422, "INVALID_INSTRUMENT", str(error)) from error
    return InstrumentResponse.from_record(instrument)


@router.get("/{instrument_id}", response_model=InstrumentDetailResponse)
async def detail(
    instrument_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> InstrumentDetailResponse:
    instrument, identifiers = await InstrumentService(db).get(instrument_id)
    return InstrumentDetailResponse(
        **InstrumentResponse.from_record(instrument).model_dump(),
        identifiers=[IdentifierResponse.from_record(item) for item in identifiers],
    )


@router.patch("/{instrument_id}", response_model=InstrumentResponse)
async def update(
    instrument_id: UUID,
    payload: InstrumentUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> InstrumentResponse:
    instrument = await InstrumentService(db).update(
        instrument_id, payload.model_dump(exclude_unset=True), actor_user_id=context.user.id
    )
    return InstrumentResponse.from_record(instrument)


@router.post("/{instrument_id}/identifiers", response_model=IdentifierResponse, status_code=201)
async def add_identifier(
    instrument_id: UUID,
    payload: IdentifierUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> IdentifierResponse:
    try:
        item = await InstrumentService(db).set_identifier(
            instrument_id,
            payload.type,
            payload.value,
            valid_from=payload.valid_from,
            source_id=None,
            raw_ingestion_id=None,
            actor_user_id=context.user.id,
        )
    except ValueError as error:
        raise AppError(422, "INVALID_IDENTIFIER", str(error)) from error
    return IdentifierResponse.from_record(item)


@router.post("/{instrument_id}/mapping")
async def request_mapping(
    instrument_id: UUID,
    payload: MappingRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> dict[str, object]:
    instrument, _ = await InstrumentService(db).get(instrument_id)
    require_data_operator(_context.user)
    result = await OpenFigiProvider(db).map_identifier(
        kind=payload.type,
        value=payload.value,
        exchange=instrument.exchange,
    )
    return {
        "status": result.status,
        "raw_ingestion_id": str(result.raw_ingestion_id),
        "candidates": [candidate.__dict__ for candidate in result.candidates],
    }


@router.post("/{instrument_id}/mapping/accept", status_code=204)
async def accept_mapping(
    instrument_id: UUID,
    payload: MappingAcceptRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> None:
    await MappingService(db).accept(
        instrument_id=instrument_id,
        raw_ingestion_id=payload.raw_ingestion_id,
        figi=payload.figi,
        actor_user_id=context.user.id,
    )
