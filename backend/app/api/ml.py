from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.db.session import get_session
from app.ml.training import TrainingInput
from app.models import MLModelVersion, MLTrainingRun
from app.services.auth import AuthContext
from app.services.ml_datasets import MLDatasetService
from app.services.ml_monitoring import MLMonitoringService
from app.services.ml_readiness import P7DataReadinessService
from app.services.ml_registry import ModelRegistryService, ModelReviewInput
from app.services.ml_training import ModelTrainingService

router = APIRouter(prefix="/api/v1/ml", tags=["machine learning"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.get("/monitoring")
async def monitoring(db: DB, context: Auth) -> dict[str, Any]:
    return await MLMonitoringService(db).report(context.user.id)


class CompositionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_ids: list[UUID] = Field(min_length=2, max_length=8)


@router.get("/datasets/readiness")
async def readiness(
    dataset_id: UUID,
    db: DB,
    context: Auth,
    horizon: Literal["30", "90"] = "30",
    required_features: Annotated[list[str] | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    return await P7DataReadinessService(db).report(
        dataset_id, context.user.id, required_features or [], int(horizon)
    )


@router.post("/datasets/compose", status_code=201)
async def compose(body: CompositionInput, db: DB, context: Auth) -> dict[str, Any]:
    dataset = await MLDatasetService(db).compose(body.window_ids, context.user.id)
    await db.commit()
    return view(dataset)


@router.post("/train", status_code=202)
async def train(body: TrainingInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ModelTrainingService(db).queue(body, context.user))


@router.get("/training-runs")
async def training_runs(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        view(r)
        for r in (
            await db.scalars(
                select(MLTrainingRun)
                .where(MLTrainingRun.user_id == context.user.id)
                .order_by(MLTrainingRun.created_at.desc())
                .limit(100)
            )
        ).all()
    ]


@router.get("/training-runs/{run_id}")
async def training_run(run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ModelTrainingService(db).owned(run_id, context.user.id))


@router.post("/training-runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    from datetime import UTC, datetime

    from app.jobs.celery_app import celery_app
    from app.services.ml_training import require_ml_operator

    require_ml_operator(context.user)
    row = await ModelTrainingService(db).owned(run_id, context.user.id)
    if row.status in {"QUEUED", "RUNNING"}:
        row.status, row.completed_at = "CANCELLED", datetime.now(UTC)
        await db.commit()
        celery_app.control.revoke(row.celery_task_id, terminate=True, signal="SIGTERM")
    return view(row)


@router.get("/models")
async def models(db: DB, context: Auth) -> list[dict[str, Any]]:
    registry = ModelRegistryService(db)
    return [
        {**view(r), "status": await registry.status(r.id)}
        for r in (
            await db.scalars(
                select(MLModelVersion)
                .where(MLModelVersion.user_id == context.user.id)
                .order_by(MLModelVersion.created_at.desc())
                .limit(100)
            )
        ).all()
    ]


@router.get("/models/{model_id}")
async def model(model_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    registry = ModelRegistryService(db)
    row = await registry.owned(model_id, context.user.id)
    return {**view(row), "status": await registry.status(row.id)}


@router.get("/models/{model_id}/evaluation")
async def model_evaluation(model_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return (await ModelRegistryService(db).owned(model_id, context.user.id)).evaluation


@router.post("/models/{model_id}/review")
async def review_model(
    model_id: UUID, body: ModelReviewInput, db: DB, context: Auth
) -> dict[str, Any]:
    return view(await ModelRegistryService(db).review(model_id, body, context.user))
