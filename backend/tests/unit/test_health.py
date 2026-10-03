from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.health import probe_services
from app.main import create_app


def test_liveness_does_not_depend_on_services() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "services": {}}
    assert response.headers["X-Request-ID"]


def test_ready_reports_real_probe_result_and_503() -> None:
    app = create_app()

    async def degraded() -> dict[str, str]:
        return {"database": "ok", "valkey": "ok", "minio": "unavailable"}

    app.dependency_overrides[probe_services] = degraded
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready", headers={"X-Request-ID": "test-123"})
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "services": {"database": "ok", "valkey": "ok", "minio": "unavailable"},
    }
    assert response.headers["X-Request-ID"] == "test-123"


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/live", headers={"X-Request-ID": "bad value"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad value"
