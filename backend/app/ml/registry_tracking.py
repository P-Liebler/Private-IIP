import httpx

from app.core.config import get_settings


def sync_status(model_id: str, run_id: str | None, status: str) -> bool:
    settings = get_settings()
    if not run_id or not settings.mlflow_tracking_username or not settings.mlflow_tracking_password:
        return False
    with httpx.Client(
        base_url=settings.mlflow_tracking_uri,
        auth=(
            settings.mlflow_tracking_username,
            settings.mlflow_tracking_password.get_secret_value(),
        ),
        timeout=httpx.Timeout(15, connect=5),
    ) as client:
        response = client.post(
            "/api/2.0/mlflow/runs/set-tag",
            json={"run_id": run_id, "key": "application_status", "value": status},
        )
        response.raise_for_status()
        name = "private-iip-" + model_id
        if status in {"PRODUCTION", "SHADOW", "VALIDATION"}:
            alias = "champion" if status == "PRODUCTION" else "challenger"
            response = client.post(
                "/api/2.0/mlflow/registered-models/alias",
                json={"name": name, "alias": alias, "version": "1"},
            )
            response.raise_for_status()
        if status != "PRODUCTION":
            response = client.delete(
                "/api/2.0/mlflow/registered-models/alias",
                params={"name": name, "alias": "champion"},
            )
            if response.status_code not in {200, 404}:
                response.raise_for_status()
    return True
