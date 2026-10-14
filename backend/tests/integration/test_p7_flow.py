import asyncio
import hashlib
import json
import secrets
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.ml.promotion import PROMOTION_RULES
from app.ml.training import TrainingInput
from app.models import (
    AuditEvent,
    DatasetVersion,
    Instrument,
    MLModelVersion,
    MLTrainingRun,
    ModelPromotionReview,
    Prediction,
    PredictionOutcome,
    SessionRecord,
    UniverseDefinition,
    User,
)
from app.services.auth import AuthService
from app.services.fundamentals import digest
from app.services.ml_registry import ModelRegistryService, ModelReviewInput
from app.services.ml_training import ModelTrainingService
from app.services.pit_datasets import code_manifest
from tests.integration.test_market_foundation import MemoryStorage


@pytest.mark.integration
def test_p7_registry_auth_immutable_predictions_and_insufficient_history(monkeypatch):
    async def run():
        password = secrets.token_urlsafe(32)
        users, instrument_id, universe_id, dataset_id = [], uuid4(), uuid4(), uuid4()
        storage = MemoryStorage()
        monkeypatch.setattr("app.services.ml_registry.get_storage", lambda: storage)
        async with get_session_factory()() as db:
            try:
                user = await AuthService(db).create_user("p7_" + uuid4().hex[:12], password)
                other = await AuthService(db).create_user("p7_" + uuid4().hex[:12], password)
                users = [user.id, other.id]
                usernames = [user.username, other.username]
                db.add(
                    Instrument(
                        id=instrument_id,
                        name="SYNTHETIC P7 integration only",
                        asset_type="STOCK",
                        currency="USD",
                        exchange="NYSE",
                    )
                )
                db.add(
                    UniverseDefinition(
                        id=universe_id,
                        user_id=user.id,
                        name="SYNTHETIC P7 empty universe",
                        configuration={"synthetic": True},
                    )
                )
                await db.flush()
                configuration = {
                    "universe_id": str(universe_id),
                    "benchmark_id": str(instrument_id),
                    "target_horizon": 30,
                    "availability_mode": "STRICT_PIT",
                    "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE",
                }
                manifest = {
                    "versions": {},
                    "version_hashes": {},
                    "feature_snapshot_ids": [],
                    "market": {},
                    "actions": {},
                }
                quality = {"survivorship_risk": False}
                db.add(
                    DatasetVersion(
                        id=dataset_id,
                        user_id=user.id,
                        universe_id=universe_id,
                        configuration=configuration,
                        manifest=manifest,
                        rows=[],
                        quality=quality,
                        content_hash=digest(
                            {
                                "configuration": configuration,
                                "manifest": manifest,
                                "rows": [],
                                "quality": quality,
                            }
                        ),
                    )
                )
                await db.commit()
                config = TrainingInput(
                    dataset_id=dataset_id,
                    model_type="LOGISTIC",
                    target="classification",
                    feature_names=["momentum_20d"],
                    required_features=["momentum_20d"],
                    folds=[
                        {
                            "validation_start": "2020-01-02T00:00:00Z",
                            "calibration_start": "2021-01-04T00:00:00Z",
                            "test_start": "2023-01-03T00:00:00Z",
                            "final_end": "2025-01-01T00:00:00Z",
                            "embargo_sessions": 30,
                        }
                    ],
                )
                request = {
                    "request": config.model_dump(mode="json"),
                    "code": code_manifest(),
                    "promotion_rules": PROMOTION_RULES,
                }
                job = MLTrainingRun(
                    user_id=users[0],
                    dataset_id=dataset_id,
                    configuration=request,
                    status="QUEUED",
                    progress=0,
                    current_stage="QUEUED",
                )
                db.add(job)
                await db.commit()
                job_id = job.id
                assert await ModelTrainingService(db).execute(job_id) is None
                await db.refresh(job)
                assert job.status == "FAILED" and job.error_code == "INSUFFICIENT_PARTITION_HISTORY"
                # This explicitly synthetic registry fixture tests persistence,
                # never model efficacy or promotion. It has no fitted forecasts.
                fixture_job = MLTrainingRun(
                    user_id=users[0],
                    dataset_id=dataset_id,
                    configuration=request,
                    status="COMPLETED",
                    progress=100,
                    current_stage="SYNTHETIC_REGISTRY_TEST",
                )
                db.add(fixture_job)
                await db.flush()
                artifact = {
                    "contract": "internal-data-only-model-v1",
                    "configuration": request["request"],
                    "training_code": request["code"],
                    "fold_models": [],
                }
                data = json.dumps(artifact).encode()
                sha = hashlib.sha256(data).hexdigest()
                key = f"model-artifacts/{fixture_job.id}/{sha}.json"
                storage.put(key, data)
                model = MLModelVersion(
                    user_id=users[0],
                    training_run_id=fixture_job.id,
                    dataset_id=dataset_id,
                    model_type="LOGISTIC",
                    target_type="classification",
                    horizon=30,
                    configuration=request,
                    evaluation={
                        "promotion_rules": PROMOTION_RULES,
                        "promotion_evidence": {
                            "synthetic_evidence": True,
                            "production_data_eligible": False,
                        },
                    },
                    artifact_key=key,
                    artifact_hash=sha,
                    content_hash=digest(artifact),
                )
                db.add(model)
                await db.flush()
                model_id = model.id
                review = ModelPromotionReview(
                    model_id=model_id,
                    reviewer_id=users[0],
                    status="SHADOW",
                    evidence={"origin": "SYNTHETIC_TEST_ONLY"},
                )
                db.add(review)
                await db.commit()
                review_id = review.id
                monkeypatch.setattr(get_settings(), "ml_operator_usernames", [usernames[0]])
                with pytest.raises(AppError, match="SYNTHETIC_EVIDENCE_FORBIDDEN"):
                    await ModelRegistryService(db).review(
                        model_id,
                        ModelReviewInput(
                            status="PRODUCTION",
                            rationale="Synthetic evaluation can never approve real forecasts",
                        ),
                        await db.get(User, users[0]),
                    )
                await db.rollback()
                app = create_app()
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                    headers={"Origin": "http://localhost:3000"},
                ) as client:
                    assert (await client.get("/api/v1/ml/models")).status_code == 401
                    assert (
                        await client.post(
                            "/api/v1/auth/login",
                            json={"username": usernames[0], "password": password},
                        )
                    ).status_code == 200
                    response = await client.get(
                        f"/api/v1/instruments/{instrument_id}/forecast?horizon=30"
                    )
                    assert response.status_code == 200, response.text
                    prediction_id = response.json()["id"]
                    assert response.json()["result"]["confidence_status"] == "NO RELIABLE FORECAST"
                    assert (
                        await client.post(f"/api/v1/predictions/{prediction_id}/evaluate")
                    ).json()["status"] == "OUTCOME_UNAVAILABLE"
                    assert (
                        await client.get(f"/api/v1/ml/datasets/readiness?dataset_id={dataset_id}")
                    ).json()["production_data_eligible"] is False
                    assert (await client.get("/api/v1/ml/monitoring")).json()[
                        "abstention_count"
                    ] == 1
                    await client.post("/api/v1/auth/logout")
                    await client.post(
                        "/api/v1/auth/login", json={"username": usernames[1], "password": password}
                    )
                    assert (await client.get(f"/api/v1/ml/models/{model_id}")).status_code == 404
                    assert (
                        await client.get(f"/api/v1/ml/training-runs/{job_id}")
                    ).status_code == 404
                    assert (
                        await client.post(f"/api/v1/predictions/{prediction_id}/evaluate")
                    ).status_code == 404
                for model_class, row_id in [
                    (MLModelVersion, model_id),
                    (ModelPromotionReview, review_id),
                ]:
                    with pytest.raises(DBAPIError):
                        await db.execute(
                            update(model_class)
                            .where(model_class.id == row_id)
                            .values(created_at=datetime.now(UTC))
                        )
                    await db.rollback()
                prediction = await db.scalar(
                    select(Prediction).where(Prediction.user_id == users[0])
                )
                pid = prediction.id
                with pytest.raises(DBAPIError):
                    await db.execute(
                        update(Prediction)
                        .where(Prediction.id == pid)
                        .values(result={"confidence_status": "FABRICATED"})
                    )
                await db.rollback()
                assert (await db.get(Prediction, pid)).result[
                    "confidence_status"
                ] == "NO RELIABLE FORECAST"
            finally:
                await db.rollback()
                for model_class, condition in [
                    (
                        PredictionOutcome,
                        PredictionOutcome.prediction_id.in_(
                            select(Prediction.id).where(Prediction.user_id.in_(users))
                        ),
                    ),
                    (Prediction, Prediction.user_id.in_(users)),
                    (
                        ModelPromotionReview,
                        ModelPromotionReview.model_id.in_(
                            select(MLModelVersion.id).where(MLModelVersion.user_id.in_(users))
                        ),
                    ),
                    (MLModelVersion, MLModelVersion.user_id.in_(users)),
                    (MLTrainingRun, MLTrainingRun.user_id.in_(users)),
                    (DatasetVersion, DatasetVersion.id == dataset_id),
                    (UniverseDefinition, UniverseDefinition.id == universe_id),
                    (Instrument, Instrument.id == instrument_id),
                    (AuditEvent, AuditEvent.actor_user_id.in_(users)),
                    (SessionRecord, SessionRecord.user_id.in_(users)),
                    (User, User.id.in_(users)),
                ]:
                    await db.execute(delete(model_class).where(condition))
                await db.commit()

    async def dispose():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(dispose())
