from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.db.session import get_session
from app.schemas.sources import DataSourceResponse
from app.services.auth import AuthContext
from app.services.sources import SourceService

router = APIRouter(prefix="/api/v1/data-sources", tags=["data sources"])


@router.get("", response_model=list[DataSourceResponse])
async def list_sources(
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> list[DataSourceResponse]:
    return [DataSourceResponse.from_record(item) for item in await SourceService(db).list()]
