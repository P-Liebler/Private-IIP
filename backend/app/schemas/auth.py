from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class UserPublic(BaseModel):
    id: UUID
    username: str
    totp_enabled: bool


class AuthenticatedLoginResponse(BaseModel):
    status: Literal["authenticated"] = "authenticated"
    user: UserPublic


class TotpRequiredResponse(BaseModel):
    status: Literal["totp_required"] = "totp_required"
    challenge: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: UserPublic | None = None


class TotpVerifyRequest(StrictModel):
    challenge: str = Field(min_length=32, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")
    code: str = Field(pattern=r"^[0-9]{6}$")


class TotpConfirmRequest(StrictModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class TotpSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TotpStatusResponse(BaseModel):
    totp_enabled: bool
