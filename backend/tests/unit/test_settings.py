from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings


def local_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://user:password@postgres:5432/investment",
        "valkey_url": "redis://valkey:6379/0",
        "minio_endpoint": "minio:9000",
        "minio_access_key": "user",
        "minio_secret_key": "long-local-password",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_local_settings_load_and_keep_timezone() -> None:
    settings = local_settings()
    assert settings.app_env == "local"
    assert settings.default_timezone == "Europe/Zurich"
    assert settings.base_currency == "CHF"


def test_test_environment_loads_without_production_requirements() -> None:
    settings = local_settings(app_env="test")
    assert settings.app_env == "test"
    assert settings.minio_secure is False


def test_production_rejects_development_credentials() -> None:
    with pytest.raises(ValidationError, match="development credentials"):
        local_settings(app_env="production", minio_secure=True, minio_secret_key="dev-only-secret")


def test_production_requires_secure_object_storage() -> None:
    with pytest.raises(ValidationError, match="MINIO_SECURE"):
        local_settings(app_env="production")


def test_invalid_totp_key_does_not_appear_in_error() -> None:
    invalid_key = "invalid-test-key-value"
    with pytest.raises(ValidationError) as caught:
        local_settings(totp_encryption_key=invalid_key)
    assert invalid_key not in str(caught.value)


def test_production_requires_secure_cookie_and_https_origins() -> None:
    base: dict[str, object] = {
        "app_env": "production",
        "database_url": "postgresql+asyncpg://user:password@postgres:5432/investment",
        "minio_secret_key": "not-a-development-secret",
        "minio_secure": True,
        "frontend_origin": "https://investments.example",
        "api_public_origin": "https://api.investments.example",
        "totp_encryption_key": Fernet.generate_key().decode(),
    }
    with pytest.raises(ValidationError, match="SESSION_SECURE_COOKIE"):
        local_settings(**base, session_secure_cookie=False)
    with pytest.raises(ValidationError, match="API_PUBLIC_ORIGIN"):
        local_settings(
            **(base | {"session_secure_cookie": True, "api_public_origin": "http://localhost:8000"})
        )
