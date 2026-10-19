from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_debug: bool = False
    database_url: str
    valkey_url: str
    minio_endpoint: str
    minio_access_key: str = Field(min_length=3)
    minio_secret_key: str = Field(min_length=8)
    minio_bucket_raw: str = "raw-ingestions"
    minio_secure: bool = False
    minio_ca_cert_path: str | None = None
    base_currency: str = "CHF"
    fx_max_carry_days: int = Field(default=5, ge=0, le=10)
    default_timezone: str = "Europe/Zurich"
    frontend_origin: str = "http://localhost:3000"
    api_public_origin: str = "http://localhost:8000"
    session_cookie_name: str = Field(default="investment_session", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    session_ttl_hours: int = Field(default=168, ge=1, le=720)
    session_secure_cookie: bool = False
    auth_login_max_attempts: int = Field(default=5, ge=1, le=100)
    auth_login_window_seconds: int = Field(default=900, ge=30, le=86400)
    totp_encryption_key: SecretStr | None = None
    openfigi_api_key: SecretStr | None = None
    openfigi_base_url: str = "https://api.openfigi.com"
    sec_user_agent: str = ""
    sec_contact_email: str = ""
    sec_base_url: str = "https://data.sec.gov"
    sec_rate_limit: int = Field(default=5, ge=1, le=10)
    sec_enabled: bool = False
    research_collection_contracts: str = "[]"
    code_commit: str = "UNVERIFIED"
    p6_max_instruments: int = Field(default=30, ge=1, le=100)
    p6_max_sessions: int = Field(default=400, ge=1, le=1000)
    p6_max_concurrent_runs: int = Field(default=1, ge=1, le=4)
    p6_timeout_seconds: int = Field(default=240, ge=10, le=600)
    ml_operator_usernames: list[str] = Field(default_factory=list)
    ml_training_timeout_seconds: int = Field(default=300, ge=30, le=600)
    ml_max_pending_jobs: int = Field(default=2, ge=1, le=5)
    p8_max_instruments: int = Field(default=30, ge=1, le=100)
    p8_timeout_seconds: int = Field(default=120, ge=10, le=300)
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_tracking_username: str = ""
    mlflow_tracking_password: SecretStr | None = None
    ollama_base_url: str = "http://ollama:11434"
    ollama_chat_model: str = Field(default="qwen3:0.6b", pattern=r"^[A-Za-z0-9._:-]{1,100}$")
    ollama_embedding_model: str = Field(
        default="embeddinggemma:300m", pattern=r"^[A-Za-z0-9._:-]{1,100}$"
    )
    assistant_timeout_seconds: int = Field(default=60, ge=5, le=120)
    assistant_context_tokens: int = Field(default=4096, ge=1024, le=8192)
    assistant_output_tokens: int = Field(default=384, ge=64, le=1024)
    assistant_chat_retention_days: int = Field(default=30, ge=1, le=365)
    assistant_test_mode: bool = False
    data_operator_usernames: list[str] = Field(default_factory=list)
    data_collection_enabled: bool = False
    forward_shadow_enabled: bool = False
    data_collection_schedules: str = "[]"
    max_daily_provider_requests: int = Field(default=100, ge=1, le=10000)
    fred_api_key: SecretStr | None = None
    alpha_vantage_api_key: SecretStr | None = None

    @field_validator("totp_encryption_key", mode="before")
    @classmethod
    def empty_key_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("openfigi_api_key", "fred_api_key", "alpha_vantage_api_key", mode="before")
    @classmethod
    def empty_openfigi_key_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_insecure_production_settings(self) -> Settings:
        if self.ollama_base_url not in {
            "http://ollama:11434",
            "http://127.0.0.1:11434",
            "http://localhost:11434",
        }:
            raise ValueError("Ollama must use the configured private local runtime")
        if self.assistant_test_mode and self.app_env != "test":
            raise ValueError("Assistant stub is restricted to APP_ENV=test")
        for origin in (self.frontend_origin, self.api_public_origin):
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Origins must be absolute HTTP(S) origins without paths")
        if self.totp_encryption_key is not None:
            try:
                Fernet(self.totp_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError) as error:
                raise ValueError("TOTP_ENCRYPTION_KEY must be a valid Fernet key") from error
        if not self.openfigi_base_url.startswith("https://") or self.openfigi_base_url.endswith(
            "/v3/mapping"
        ):
            raise ValueError("OPENFIGI_BASE_URL must be an HTTPS service origin")
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
            if not self.api_public_origin.startswith("https://"):
                raise ValueError("API_PUBLIC_ORIGIN must use HTTPS in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
