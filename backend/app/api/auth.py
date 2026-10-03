from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.auth import (
    AuthenticatedLoginResponse,
    LoginRequest,
    SessionResponse,
    TotpConfirmRequest,
    TotpRequiredResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    UserPublic,
)
from app.services.auth import AuthContext, AuthenticatedLogin, AuthService, client_ip_address

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _ip(request: Request) -> str:
    return client_ip_address(request.client.host if request.client else None)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_secure_cookie,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _user_public(context: AuthContext | AuthenticatedLogin) -> UserPublic:
    user = context.user
    return UserPublic(id=user.id, username=user.username, totp_enabled=user.totp_enabled)


@router.post("/login", response_model=AuthenticatedLoginResponse | TotpRequiredResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AuthenticatedLoginResponse | TotpRequiredResponse:
    result = await AuthService(db).login(
        payload.username,
        payload.password,
        ip_address=_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    if isinstance(result, AuthenticatedLogin):
        _set_session_cookie(response, result.token)
        return AuthenticatedLoginResponse(user=_user_public(result))
    response.status_code = 202
    response.headers["Cache-Control"] = "no-store"
    return TotpRequiredResponse(challenge=result.challenge)


@router.post("/totp/verify", response_model=AuthenticatedLoginResponse)
async def verify_totp(
    payload: TotpVerifyRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AuthenticatedLoginResponse:
    result = await AuthService(db).verify_totp_challenge(
        payload.challenge,
        payload.code,
        ip_address=_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    _set_session_cookie(response, result.token)
    return AuthenticatedLoginResponse(user=_user_public(result))


@router.get("/session", response_model=SessionResponse)
async def session(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SessionResponse:
    token = request.cookies.get(get_settings().session_cookie_name)
    context, _ = await AuthService(db).authenticate(token)
    response.headers["Cache-Control"] = "no-store"
    if context is None:
        if token is not None:
            response.delete_cookie(get_settings().session_cookie_name, path="/")
        return SessionResponse(authenticated=False)
    return SessionResponse(authenticated=True, user=_user_public(context))


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> None:
    await AuthService(db).logout(context, ip_address=_ip(request))
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    response.headers["Cache-Control"] = "no-store"


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def setup_totp(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> JSONResponse:
    secret, uri = await AuthService(db).start_totp(context, ip_address=_ip(request))
    return JSONResponse(
        content=TotpSetupResponse(secret=secret, provisioning_uri=uri).model_dump(),
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post("/totp/confirm", response_model=TotpStatusResponse)
async def confirm_totp(
    payload: TotpConfirmRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[AuthContext, Depends(require_user)],
) -> TotpStatusResponse:
    user = await AuthService(db).confirm_totp(context, payload.code, ip_address=_ip(request))
    return TotpStatusResponse(totp_enabled=user.totp_enabled)
