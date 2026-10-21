"""Run inside the isolated restore API container against an explicit test fixture."""

from __future__ import annotations

import asyncio
import hashlib
import os
from decimal import Decimal
from uuid import UUID

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text

from app.api.research import view
from app.core.storage import get_storage
from app.db.session import get_session_factory
from app.models import Portfolio, Prediction, PredictionOutcome, Transaction, User
from app.services.fundamentals import digest
from app.services.ml_registry import ModelRegistryService
from app.services.pit_datasets import DatasetBuilder
from app.services.raw_ingestion import RawIngestionService
from app.services.risk_audit import history_checkpoint


async def main() -> None:
    username = os.environ["RESTORE_TEST_USERNAME"]
    password = os.environ["RESTORE_TEST_PASSWORD"]
    portfolio_id = UUID(os.environ["RESTORE_TEST_PORTFOLIO_ID"])
    raw_id = UUID(os.environ["RESTORE_TEST_RAW_ID"])
    expected = Decimal(os.environ["RESTORE_TEST_VALUE"])
    async with get_session_factory()() as db:
        from app.services.validation_audit import validation_checkpoint

        expected_validation = os.environ.get("RESTORE_TEST_VALIDATION_HISTORY_HASH")
        if expected_validation:
            checkpoint = await validation_checkpoint(db)
            assert checkpoint["validation_history_hash"] == expected_validation, (
                "PR2 validation evidence/links checkpoint mismatch"
            )
            print(f"PR2 restored validation evidence: {checkpoint['records']} records verified")
        from app.services.collection_audit import collection_checkpoint

        expected_collections = os.environ.get("RESTORE_TEST_COLLECTIONS_HISTORY_HASH")
        if expected_collections:
            checkpoint = await collection_checkpoint(db)
            assert checkpoint["collections_history_hash"] == expected_collections, (
                "Collector/source/canonical checkpoint mismatch"
            )
        revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
        expected_head = (
            os.environ.get("RESTORE_EXPECTED_REVISION")
            or ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        )
        assert revision == expected_head, "Migration head mismatch"
        user = await db.scalar(select(User).where(User.username == username))
        assert user is not None and user.is_active, "Fixture user missing"
        portfolio = await db.get(Portfolio, portfolio_id)
        assert portfolio is not None and portfolio.user_id == user.id, "Fixture portfolio missing"
        rows = (
            await db.scalars(select(Transaction).where(Transaction.portfolio_id == portfolio_id))
        ).all()
        assert rows, "Fixture transactions missing"
        raw = await RawIngestionService(db).get_verified(raw_id)
        assert raw, "Fixture raw object empty"
        dataset_id = os.environ.get("RESTORE_TEST_DATASET_ID")
        if dataset_id:
            replay = await DatasetBuilder(db).rebuild(UUID(dataset_id), user.id)
            assert replay["content_hash"] == os.environ["RESTORE_TEST_DATASET_HASH"], (
                "Restored dataset hash mismatch"
            )
            print("P6 restored dataset: pinned versions, raw bytes and manifest verified")
        model_id = os.environ.get("RESTORE_TEST_MODEL_ID")
        if model_id:
            model = await ModelRegistryService(db).owned(UUID(model_id), user.id)
            assert model.artifact_hash == os.environ["RESTORE_TEST_ARTIFACT_HASH"]
            await ModelRegistryService(db).artifact(model)
            await DatasetBuilder(db).rebuild(model.dataset_id, user.id)
            if model.mlflow_run_id:
                assert (
                    await db.scalar(
                        text("SELECT count(*) FROM iip_mlflow.runs WHERE run_uuid=:run_id"),
                        {"run_id": model.mlflow_run_id},
                    )
                    == 1
                )
                artifact_uri = await db.scalar(
                    text("SELECT artifact_uri FROM iip_mlflow.runs WHERE run_uuid=:run_id"),
                    {"run_id": model.mlflow_run_id},
                )
                relative = artifact_uri.removeprefix("mlflow-artifacts:/").lstrip("/")
                tracked_data = get_storage().get("mlflow-artifacts/" + relative + "/model.json")
                assert hashlib.sha256(tracked_data).hexdigest() == model.artifact_hash
            print("P7 restored model: internal artifact hash, dataset and MLflow metadata verified")
        expected_predictions = os.environ.get("RESTORE_TEST_PREDICTION_HISTORY_HASH")
        if expected_predictions:
            predictions = (
                await db.scalars(
                    select(Prediction).where(Prediction.user_id == user.id).order_by(Prediction.id)
                )
            ).all()
            outcomes = (
                await db.scalars(
                    select(PredictionOutcome)
                    .where(PredictionOutcome.prediction_id.in_([p.id for p in predictions]))
                    .order_by(PredictionOutcome.id)
                )
            ).all()
            assert (
                digest(
                    {
                        "predictions": [view(p) for p in predictions],
                        "outcomes": [view(o) for o in outcomes],
                    }
                )
                == expected_predictions
            )
            print("P7 restored prediction/outcome history: exact content hash verified")
        expected_intelligence = os.environ.get("RESTORE_TEST_INTELLIGENCE_HISTORY_HASH")
        if expected_intelligence:
            from app.assistant.audit import intelligence_checkpoint

            checkpoint = await intelligence_checkpoint(db, user.id)
            assert checkpoint["intelligence_history_hash"] == expected_intelligence
            assert checkpoint["document_count"] and checkpoint["embedding_count"]
            assert checkpoint["brief_count"] and checkpoint["alert_evaluation_count"]
            assert checkpoint["calendar_version_count"] >= 2 and checkpoint["alert_event_count"]
            assert checkpoint["optimizer_count"] and checkpoint["message_count"]
            print("P10 restored private metadata, raw PDFs, chunks and exact embeddings verified")
        expected_recommendations = os.environ.get("RESTORE_TEST_RECOMMENDATION_HISTORY_HASH")
        if expected_recommendations:
            from app.recommendations.audit import recommendation_checkpoint

            checkpoint = await recommendation_checkpoint(db, user.id)
            assert checkpoint["recommendation_history_hash"] == expected_recommendations
            assert checkpoint["recommendation_count"] and checkpoint["profile_count"]
            print("P9 restored profiles, rules, reviews and recommendations: exact replay verified")
        expected_risk_history = os.environ.get("RESTORE_TEST_RISK_HISTORY_HASH")
        if expected_risk_history:
            checkpoint = await history_checkpoint(db, user.id, portfolio_id, verify=True)
            assert checkpoint["risk_history_hash"] == expected_risk_history, (
                "Restored risk/scenario/what-if history mismatch"
            )
            assert (
                checkpoint["risk_count"]
                and checkpoint["scenario_count"]
                and checkpoint["what_if_count"]
            )
            print(
                "P8 restored risk, scenario and what-if histories: "
                "exact hashes and provenance verified"
            )
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://restore.local"},
        timeout=httpx.Timeout(30, connect=5),
    ) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        assert login.status_code == 200, "Restored login failed"
        value = await client.get(f"/api/v1/portfolios/{portfolio_id}/valuation")
        assert value.status_code == 200, "Restored valuation request failed"
        payload = value.json()
        assert payload["status"] == "COMPLETE", "Restored valuation incomplete"
        assert Decimal(payload["total_value_base"]) == expected, "Restored value mismatch"
    print("Isolated restore verified: migration, raw hash, login and portfolio valuation")


if __name__ == "__main__":
    asyncio.run(main())
