"""Provide non-secret defaults when tests run outside Docker Compose."""

import os


def pytest_configure() -> None:
    defaults = {
        "DATABASE_URL": "postgresql+asyncpg://test:test-password@postgres:5432/investment",
        "VALKEY_URL": "redis://valkey:6379/0",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "test-user",
        "MINIO_SECRET_KEY": "test-only-password",
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)
