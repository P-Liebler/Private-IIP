import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy import select

from app.db.session import get_engine, get_session_factory
from app.models import MLModelVersion, MLTrainingRun
from app.services.ml_registry import ModelRegistryService


async def inspect(job_id: UUID) -> None:
    try:
        async with get_session_factory()() as db:
            job = await db.get(MLTrainingRun, job_id)
            assert job is not None
            model = await db.scalar(
                select(MLModelVersion).where(MLModelVersion.training_run_id == job_id)
            )
            result = {
                "job_id": str(job_id),
                "status": job.status,
                "stage": job.current_stage,
                "error_code": job.error_code,
            }
            if model:
                await ModelRegistryService(db).artifact(model)
                result.update(
                    {
                        "model_id": str(model.id),
                        "artifact_key": model.artifact_key,
                        "artifact_hash": model.artifact_hash,
                        "model_status": await ModelRegistryService(db).status(model.id),
                        "mlflow_run_id": model.mlflow_run_id,
                        "tracking_status": model.evaluation.get("tracking_status"),
                        "promotion_reasons": model.evaluation["promotion_reasons"],
                        "oos_metrics": model.evaluation["aggregated_oos"],
                    }
                )
            print(json.dumps(result, indent=2))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id", type=UUID)
    asyncio.run(inspect(parser.parse_args().job_id))
