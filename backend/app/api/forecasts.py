from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.db.session import get_session
from app.models import Prediction, PredictionOutcome
from app.services.auth import AuthContext
from app.services.ml_registry import ModelRegistryService
from app.services.predictions import PredictionService

router = APIRouter(prefix="/api/v1", tags=["forecasts"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.get("/instruments/{instrument_id}/forecast")
async def forecast(
    instrument_id: UUID, db: DB, context: Auth, horizon: Literal["30", "90"] = "30"
) -> dict[str, Any]:
    previous = await db.scalar(
        select(Prediction)
        .where(
            Prediction.user_id == context.user.id,
            Prediction.instrument_id == instrument_id,
            Prediction.horizon == int(horizon),
        )
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    if (
        previous
        and previous.generated_at.date() == datetime.now(UTC).date()
        and (
            previous.model_id is None
            or previous.result["confidence_status"] != "VALIDATED"
            or await ModelRegistryService(db).status(previous.model_id) == "PRODUCTION"
        )
    ):
        return view(previous)
    return view(await PredictionService(db).generate(instrument_id, int(horizon), context.user.id))


@router.get("/instruments/{instrument_id}/prediction-history")
async def history(
    instrument_id: UUID, db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    predictions = (
        await db.scalars(
            select(Prediction)
            .where(Prediction.user_id == context.user.id, Prediction.instrument_id == instrument_id)
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    outcomes = (
        await db.scalars(
            select(PredictionOutcome)
            .where(PredictionOutcome.prediction_id.in_([p.id for p in predictions]))
            .order_by(PredictionOutcome.created_at)
        )
    ).all()
    return [
        {**view(p), "outcomes": [view(o) for o in outcomes if o.prediction_id == p.id]}
        for p in predictions
    ]


@router.post("/predictions/{prediction_id}/evaluate")
async def evaluate(prediction_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    result = await PredictionService(db).outcome(prediction_id, context.user.id)
    return (
        view(result)
        if result
        else {
            "status": "OUTCOME_UNAVAILABLE",
            "reason": "Unreliable forecast or realization inputs not fully available",
        }
    )
