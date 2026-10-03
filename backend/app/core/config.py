from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_debug: bool = False
    database_url: str
    valkey_url: str
    minio_endpoint: str
    minio_access_key: str = Field(min_length=3)
    minio_secret_key: str = Field(min_length=8)
    minio_bucket_raw: str = "raw-ingestions"
    minio_secure: bool = False
    base_currency: str = "CHF"
    default_timezone: str = "Europe/Zurich"
    frontend_origin: str = "http://localhost:3000"
    api_public_origin: str = "http://localhost:8000"
    session_cookie_name: str = Field(default="investment_session", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    session_ttl_hours: int = Field(default=168, ge=1, le=720)
    session_secure_cookie: bool = False
    auth_login_max_attempts: int = Field(default=5, ge=1, le=100)
    auth_login_window_seconds: int = Field(default=900, ge=30, le=86400)
    totp_encryption_key: SecretStr | None = None

    @field_validator("totp_encryption_key", mode="before")
    @classmethod
    def empty_key_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_insecure_production_settings(self) -> Settings:
        for origin in (self.frontend_origin, self.api_public_origin):
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
            ):
                raise ValueError("Origins must be absolute HTTP(S) origins without paths")
        if self.totp_encryption_key is not None:
            try:
                Fernet(self.totp_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError) as error:
                raise ValueError("TOTP_ENCRYPTION_KEY must be a valid Fernet key") from error
        if self.app_env == "production":
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if "dev-only" in self.database_url or "dev-only" in self.minio_secret_key:
                raise ValueError("development credentials cannot be used in production")
            if not self.minio_secure:
                raise ValueError("MINIO_SECURE must be true in production")
            if not self.session_secure_cookie:
                raise ValueError("SESSION_SECURE_COOKIE must be true in production")
            if self.totp_encryption_key is None:
                raise ValueError("TOTP_ENCRYPTION_KEY is required in production")
            if not self.frontend_origin.startswith("https://"):
                raise ValueError("FRONTEND_ORIGIN must use HTTPS in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
