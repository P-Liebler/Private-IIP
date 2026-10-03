from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.services.auth import AuthContext, AuthService


async def require_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AuthContext:
    token = request.cookies.get(get_settings().session_cookie_name)
    context, code = await AuthService(db).authenticate(token)
    if context is None:
        message = "Session expired" if code == "SESSION_EXPIRED" else "Authentication required"
        raise AppError(401, code, message)
    return context
