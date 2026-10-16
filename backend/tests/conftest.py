"""Provide non-secret defaults when tests run outside Docker Compose."""

import os
from uuid import uuid4

import pytest


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


@pytest.fixture
def isolated_provider_limits(monkeypatch):
    """Use real Valkey/Lua with fresh keys; never reset an operational budget."""
    from app.core.valkey import make_valkey_client

    prefix = f"pytest:provider:{uuid4().hex}:"

    def factory():
        client = make_valkey_client()
        original = client.eval

        async def evaluate(script, numkeys, *values):
            return await original(
                script,
                numkeys,
                *(prefix + str(v) for v in values[:numkeys]),
                *values[numkeys:],
            )

        client.eval = evaluate
        return client

    monkeypatch.setattr("app.services.provider_rate_limit.make_valkey_client", factory)
    monkeypatch.setattr("app.providers.sec.make_valkey_client", factory)
