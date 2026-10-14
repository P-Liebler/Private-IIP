"""Bounded internal MLflow REST integration; never required by portfolio reads."""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings


def track_model(
    model_id: str,
    configuration: dict[str, Any],
    metrics: dict[str, Any],
    artifact_key: str,
    artifact_hash: str,
    artifact_data: bytes,
) -> str | None:
    settings = get_settings()
    if not settings.mlflow_tracking_username or not settings.mlflow_tracking_password:
        return None
    with httpx.Client(
        base_url=settings.mlflow_tracking_uri,
        auth=(
            settings.mlflow_tracking_username,
            settings.mlflow_tracking_password.get_secret_value(),
        ),
        timeout=httpx.Timeout(15, connect=5),
    ) as client:
        response = client.get(
            "/api/2.0/mlflow/experiments/get-by-name", params={"experiment_name": "Private-IIP"}
        )
        if response.status_code == 404:
            response = client.post(
                "/api/2.0/mlflow/experiments/create", json={"name": "Private-IIP"}
            )
            response.raise_for_status()
            experiment = response.json()["experiment_id"]
        else:
            response.raise_for_status()
            experiment = response.json()["experiment"]["experiment_id"]
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={
                "experiment_id": experiment,
                "tags": [
                    {"key": "application_model_id", "value": model_id},
                    {"key": "application_status", "value": "SHADOW"},
                    {"key": "artifact_key", "value": artifact_key},
                    {"key": "artifact_sha256", "value": artifact_hash},
                ],
            },
        )
        response.raise_for_status()
        run_id = response.json()["run"]["info"]["run_id"]
        artifact_uri = response.json()["run"]["info"]["artifact_uri"]
        relative = artifact_uri.removeprefix("mlflow-artifacts:/").lstrip("/")
        response = client.put(
            "/api/2.0/mlflow-artifacts/artifacts/" + relative + "/model.json",
            content=artifact_data,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        registered_name = "private-iip-" + model_id
        response = client.post(
            "/api/2.0/mlflow/registered-models/create", json={"name": registered_name}
        )
        response.raise_for_status()
        response = client.post(
            "/api/2.0/mlflow/model-versions/create",
            json={
                "name": registered_name,
                "source": artifact_uri + "/model.json",
                "run_id": run_id,
            },
        )
        response.raise_for_status()
        version = response.json()["model_version"]["version"]
        response = client.post(
            "/api/2.0/mlflow/registered-models/alias",
            json={"name": registered_name, "alias": "challenger", "version": version},
        )
        response.raise_for_status()
        params = [
            {"key": k, "value": str(v)}
            for k, v in configuration.items()
            if k in {"model_type", "target", "horizon", "seed", "dataset_id"}
        ]
        timestamp = int(datetime.now(UTC).timestamp() * 1000)
        values = [
            {"key": k, "value": float(v), "timestamp": timestamp, "step": 0}
            for k, v in metrics.items()
            if isinstance(v, (int, float))
        ]
        response = client.post(
            "/api/2.0/mlflow/runs/log-batch",
            json={"run_id": run_id, "params": params, "metrics": values, "tags": []},
        )
        response.raise_for_status()
        response = client.post(
            "/api/2.0/mlflow/runs/update",
            json={"run_id": run_id, "status": "FINISHED", "end_time": timestamp},
        )
        response.raise_for_status()
        return str(run_id)
