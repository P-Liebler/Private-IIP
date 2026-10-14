import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy import select

from app.api.research import view
from app.db.session import get_engine, get_session_factory
from app.models import MLModelVersion, Prediction, PredictionOutcome
from app.services.fundamentals import digest


async def main(model_id: UUID) -> None:
    try:
        async with get_session_factory()() as db:
            model = await db.get(MLModelVersion, model_id)
            assert model is not None
            predictions = (
                await db.scalars(
                    select(Prediction)
                    .where(Prediction.user_id == model.user_id)
                    .order_by(Prediction.id)
                )
            ).all()
            outcomes = (
                await db.scalars(
                    select(PredictionOutcome)
                    .where(PredictionOutcome.prediction_id.in_([p.id for p in predictions]))
                    .order_by(PredictionOutcome.id)
                )
            ).all()
            print(
                json.dumps(
                    {
                        "model_id": str(model_id),
                        "artifact_hash": model.artifact_hash,
                        "prediction_history_hash": digest(
                            {
                                "predictions": [view(p) for p in predictions],
                                "outcomes": [view(o) for o in outcomes],
                            }
                        ),
                        "prediction_count": len(predictions),
                        "outcome_count": len(outcomes),
                    }
                )
            )
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id", type=UUID)
    asyncio.run(main(parser.parse_args().model_id))
