from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.db.session import get_session
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.auth import AuthContext, client_ip_address
from app.services.user_settings import UserSettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> SettingsResponse:
    user = await UserSettingsService(db).get(context.user.id)
    return SettingsResponse(timezone=user.timezone, base_currency=user.base_currency)


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> SettingsResponse:
    user = await UserSettingsService(db).update(
        context.user.id,
        payload.model_dump(exclude_unset=True),
        ip_address=client_ip_address(request.client.host if request.client else None),
    )
    return SettingsResponse(timezone=user.timezone, base_currency=user.base_currency)
