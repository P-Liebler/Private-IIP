"""Pipe into a quiesced local API container; read-only synthetic archive checkpoint.

Uses existing domain verifiers. Never rewrites archived rows or manifests.
"""
import asyncio
from datetime import UTC, datetime
import json
import os
from uuid import UUID
from sqlalchemy import select, text
from app.api.research import view
from app.assistant.audit import intelligence_checkpoint
from app.db.session import get_engine, get_session_factory
from app.models import DataSource, DatasetVersion, Portfolio, Prediction, PredictionOutcome, User
from app.recommendations.audit import recommendation_checkpoint
from app.services.collection_audit import collection_checkpoint
from app.services.fundamentals import digest
from app.services.ml_registry import ModelRegistryService
from app.services.pit_datasets import DatasetBuilder
from app.services.risk_audit import history_checkpoint
from app.services.validation_audit import validation_checkpoint


async def main():
    try:
        async with get_session_factory()() as db:
            portfolio = await db.get(Portfolio, UUID(os.environ["PR4_PORTFOLIO_ID"]))
            assert portfolio is not None
            user = await db.get(User, portfolio.user_id)
            assert user and user.username.startswith("restore_")
            model = await ModelRegistryService(db).owned(UUID(os.environ["PR4_MODEL_ID"]), user.id)
            await ModelRegistryService(db).artifact(model)
            replay = await DatasetBuilder(db).rebuild(UUID(os.environ["PR4_DATASET_ID"]), user.id)
            dataset = await db.get(DatasetVersion, UUID(os.environ["PR4_DATASET_ID"]))
            assert dataset and replay["content_hash"] == dataset.content_hash
            predictions = (await db.scalars(select(Prediction).where(Prediction.user_id == user.id).order_by(Prediction.id))).all()
            outcomes = (await db.scalars(select(PredictionOutcome).where(PredictionOutcome.prediction_id.in_([row.id for row in predictions])).order_by(PredictionOutcome.id))).all()
            result = {"recorded_at": datetime.now(UTC).isoformat(), "scope": "LOCAL_SYNTHETIC_ARCHIVES",
                      "username": user.username, "portfolio_id": str(portfolio.id), "model_id": str(model.id),
                      "dataset_id": str(dataset.id), "dataset_hash": dataset.content_hash,
                      "model_artifact_hash": model.artifact_hash,
                      "prediction_history_hash": digest({"predictions": [view(row) for row in predictions], "outcomes": [view(row) for row in outcomes]}),
                      "prediction_count": len(predictions), "outcome_count": len(outcomes),
                      "schema_head": await db.scalar(text("SELECT version_num FROM alembic_version"))}
            sources = (await db.scalars(select(DataSource).order_by(DataSource.slug))).all()
            result["source_gates"] = {source.slug: {"status": source.gate_status, "enabled": source.enabled} for source in sources}
            for checkpoint in (await history_checkpoint(db, user.id, portfolio.id, verify=True),
                               await recommendation_checkpoint(db, user.id),
                               await intelligence_checkpoint(db, user.id),
                               await collection_checkpoint(db), await validation_checkpoint(db)):
                result.update(checkpoint)
            print(json.dumps(result))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
