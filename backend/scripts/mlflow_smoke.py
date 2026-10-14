"""Explicit internal smoke artifact, never a financial model or forecast."""

import hashlib
import json
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.storage import get_storage
from app.ml.tracking import track_model


def main() -> None:
    settings = get_settings()
    if settings.app_env not in {"local", "test"}:
        raise RuntimeError("Local/test smoke only")
    assert settings.mlflow_tracking_password
    data = json.dumps(
        {"context": "EXPLICIT_SMOKE_NOT_A_FINANCIAL_MODEL", "id": str(uuid4())}
    ).encode()
    sha = hashlib.sha256(data).hexdigest()
    key = f"model-artifacts/smoke/{sha}.json"
    storage = get_storage()
    storage.ensure_bucket()
    storage.put(key, data, "application/json")
    run_id = track_model(
        "smoke-" + uuid4().hex,
        {"model_type": "SMOKE_NOT_A_MODEL", "target": "NONE", "seed": 71},
        {"smoke": 1},
        key,
        sha,
        data,
    )
    assert run_id
    with httpx.Client(base_url=settings.mlflow_tracking_uri, timeout=10) as client:
        assert client.get("/api/2.0/mlflow/runs/get", params={"run_id": run_id}).status_code == 401
        client.auth = (
            settings.mlflow_tracking_username,
            settings.mlflow_tracking_password.get_secret_value(),
        )
        response = client.get("/api/2.0/mlflow/runs/get", params={"run_id": run_id})
        response.raise_for_status()
        artifact_uri = response.json()["run"]["info"]["artifact_uri"]
        relative = artifact_uri.removeprefix("mlflow-artifacts:/").lstrip("/")
        response = client.get("/api/2.0/mlflow-artifacts/artifacts/" + relative + "/model.json")
        response.raise_for_status()
        assert hashlib.sha256(response.content).hexdigest() == sha
    assert hashlib.sha256(storage.get(key)).hexdigest() == sha
    print(
        json.dumps(
            {
                "status": "PASS",
                "authentication_required": True,
                "run_id": run_id,
                "artifact_hash": sha,
                "model_artifact_key": key,
                "mlflow_artifact_key": "mlflow-artifacts/" + relative + "/model.json",
            }
        )
    )


if __name__ == "__main__":
    main()
