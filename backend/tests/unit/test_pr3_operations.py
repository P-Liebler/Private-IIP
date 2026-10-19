import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import system_status as operations
from app.api.dependencies import require_user
from app.core.errors import AppError
from app.main import create_app


def test_operations_requires_explicit_operator(monkeypatch):
    monkeypatch.setattr(
        operations, "get_settings", lambda: SimpleNamespace(operations_operator_usernames=[])
    )
    with pytest.raises(AppError) as caught:
        asyncio.run(
            operations.require_operations_operator(
                SimpleNamespace(user=SimpleNamespace(username="ordinary"))
            )
        )
    assert caught.value.status_code == 403


def test_status_redacts_paths_and_secret_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "RUNTIME", tmp_path)
    (tmp_path / "backup-status.json").write_text(
        json.dumps(
            {
                "success": False,
                "completed_at": datetime.now(UTC).isoformat(),
                "error": "sensitive error",
                "root": "private backup location",
                "password": "secret",
            }
        )
    )
    result = operations._status("backup-status.json")
    assert result["status"] == "FAILED"
    assert result["age_seconds"] >= 0
    assert "secret" not in json.dumps(result)
    assert "private backup" not in json.dumps(result)


@pytest.mark.parametrize(
    "stamp",
    ["not-a-date", (datetime.now(UTC) + timedelta(days=1)).isoformat(), "2026-01-01T00:00:00"],
)
def test_invalid_backup_evidence_is_unavailable(stamp, tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "RUNTIME", tmp_path)
    (tmp_path / "backup-status.json").write_text(
        json.dumps({"success": True, "completed_at": stamp})
    )
    assert operations._status("backup-status.json")["status"] == "UNAVAILABLE"


def test_admin_status_optional_outage_and_open_target_gates(monkeypatch):
    settings = SimpleNamespace(
        operations_operator_usernames=["operator"],
        code_commit="UNVERIFIED",
        app_env="test",
        mlflow_tracking_uri="http://mlflow:5000",
        ollama_base_url="http://ollama:11434",
        data_collection_enabled=False,
        forward_shadow_enabled=False,
    )
    monkeypatch.setattr(operations, "get_settings", lambda: settings)
    monkeypatch.setattr(
        operations,
        "probe_services",
        AsyncMock(return_value={"database": "ok", "minio": "ok", "valkey": "ok"}),
    )
    monkeypatch.setattr(operations, "worker_status", AsyncMock(return_value="HEALTHY"))
    monkeypatch.setattr(operations, "scheduler_status", AsyncMock(return_value="HEALTHY"))
    monkeypatch.setattr(operations, "optional_service", AsyncMock(return_value="UNAVAILABLE"))
    app = create_app()
    app.dependency_overrides[require_user] = lambda: SimpleNamespace(
        user=SimpleNamespace(username="operator")
    )

    async def run():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "DEGRADED"
        assert body["services"]["database"] == "HEALTHY"
        assert body["decisions"]["core"] == "PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED"
        assert body["decisions"]["forecasts"] == "FORECASTS_SHADOW_ONLY"
        assert all(value == "NOT_VERIFIED" for value in body["operator_evidence"].values())

    asyncio.run(run())


def test_system_status_denies_non_operator(monkeypatch):
    monkeypatch.setattr(
        operations, "get_settings", lambda: SimpleNamespace(operations_operator_usernames=[])
    )
    app = create_app()
    app.dependency_overrides[require_user] = lambda: SimpleNamespace(
        user=SimpleNamespace(username="ordinary")
    )

    async def run():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            assert (await client.get("/api/v1/system/status")).status_code == 403

    asyncio.run(run())
