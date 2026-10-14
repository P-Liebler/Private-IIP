import asyncio
from uuid import UUID

from app.db.session import get_engine, get_session_factory
from app.jobs.celery_app import celery_app


@celery_app.task(name="ml.train", soft_time_limit=600, time_limit=630)  # type: ignore[misc]
def train(run_id: str) -> dict[str, str]:
    from app.services.ml_training import ModelTrainingService

    async def execute() -> dict[str, str]:
        try:
            async with get_session_factory()() as db:
                model = await ModelTrainingService(db).execute(UUID(run_id))
                return {"model_id": str(model.id)} if model else {"status": "NO_MODEL_CREATED"}
        finally:
            await get_engine().dispose()

    return asyncio.run(execute())
