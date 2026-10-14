import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.storage import get_storage
from app.ml.financial import financial_evaluation
from app.ml.models import CLASSIFIERS
from app.ml.promotion import PROMOTION_RULES, promotion_reasons
from app.ml.tracking import track_model
from app.ml.training import TrainingInput, train_kernel
from app.models import Instrument, MLModelVersion, MLTrainingRun, ModelPromotionReview, User
from app.services.fundamentals import digest
from app.services.ml_readiness import P7DataReadinessService
from app.services.pit_datasets import DatasetBuilder, code_manifest


def require_ml_operator(user: User) -> None:
    if user.username not in get_settings().ml_operator_usernames:
        raise AppError(403, "ML_OPERATOR_REQUIRED", "Model administration requires an operator")


class ModelTrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def owned(self, run_id: UUID, user_id: UUID) -> MLTrainingRun:
        row = await self.db.get(MLTrainingRun, run_id)
        if row is None or row.user_id != user_id:
            raise AppError(404, "TRAINING_RUN_NOT_FOUND", "Training run not found")
        origin = row.started_at if row.status == "RUNNING" else row.created_at
        if (
            row.status in {"QUEUED", "RUNNING"}
            and origin
            and origin
            < datetime.now(UTC)
            - timedelta(
                seconds=get_settings().ml_training_timeout_seconds
                * (get_settings().ml_max_pending_jobs if row.status == "QUEUED" else 1)
                + 60
            )
        ):
            row.status, row.error_code, row.completed_at = (
                "FAILED",
                "PROCESS_INTERRUPTED",
                datetime.now(UTC),
            )
            await self.db.commit()
        return row

    async def queue(self, config: TrainingInput, user: User) -> MLTrainingRun:
        require_ml_operator(user)
        dataset = await DatasetBuilder(self.db).owned(config.dataset_id, user.id)
        if dataset.configuration["target_horizon"] != config.horizon:
            raise AppError(422, "TARGET_HORIZON_MISMATCH", "Dataset horizon differs")
        if not await self.db.scalar(text("SELECT pg_try_advisory_xact_lock(608630)")):
            raise AppError(409, "TRAINING_LIMIT", "Another training request is being queued")
        pending = await self.db.scalar(
            select(func.count())
            .select_from(MLTrainingRun)
            .where(MLTrainingRun.status.in_(["QUEUED", "RUNNING"]))
        )
        if (pending or 0) >= get_settings().ml_max_pending_jobs:
            raise AppError(409, "TRAINING_LIMIT", "Training queue is full")
        row = MLTrainingRun(
            user_id=user.id,
            dataset_id=config.dataset_id,
            configuration={
                "request": config.model_dump(mode="json"),
                "code": code_manifest(),
                "promotion_rules": PROMOTION_RULES,
                "dataset_manifest": {
                    "content_hash": dataset.content_hash,
                    "feature_version": dataset.configuration.get("feature_set_version"),
                    "target_version": dataset.manifest.get("target_version"),
                    "availability_mode": dataset.configuration.get("availability_mode"),
                },
            },
            status="QUEUED",
            progress=0,
            current_stage="QUEUED",
        )
        self.db.add(row)
        await self.db.flush()
        # A stable task identifier allows a committed queued job to be safely
        # retried by the operator without creating multiple model versions.
        row.celery_task_id = str(row.id)
        await self.db.commit()
        from app.jobs.celery_app import celery_app

        try:
            celery_app.send_task(
                "ml.train", args=[str(row.id)], task_id=row.celery_task_id, queue="ml"
            )
        except Exception as error:
            row.status, row.current_stage, row.error_code = "FAILED", "QUEUE", "QUEUE_UNAVAILABLE"
            row.completed_at = datetime.now(UTC)
            await self.db.commit()
            raise AppError(503, "QUEUE_UNAVAILABLE", "Training queue unavailable") from error
        return row

    async def execute(self, run_id: UUID) -> MLModelVersion | None:
        row = await self.db.get(MLTrainingRun, run_id, with_for_update=True)
        if row is None or row.status != "QUEUED":
            return None
        row.status, row.current_stage, row.started_at = (
            "RUNNING",
            "DATA_READINESS",
            datetime.now(UTC),
        )
        await self.db.commit()
        owner_id, config_data = row.user_id, row.configuration
        try:
            async with asyncio.timeout(get_settings().ml_training_timeout_seconds):
                config = TrainingInput.model_validate(config_data["request"])
                if code_manifest() != config_data["code"]:
                    raise ValueError("TRAINING_CODE_CHANGED_SINCE_QUEUE")
                readiness = await P7DataReadinessService(self.db).report(
                    config.dataset_id, owner_id, config.required_features, config.horizon
                )
                if readiness["status"] == "DATA_QUALITY_FAILED":
                    raise ValueError("DATA_QUALITY_FAILED")
                dataset = await DatasetBuilder(self.db).owned(config.dataset_id, owner_id)
                exchanges = {}
                for iid in sorted({r["instrument_id"] for r in dataset.rows}):
                    instrument = await self.db.get(Instrument, UUID(iid))
                    if instrument is None or not instrument.exchange:
                        raise ValueError("CALENDAR_UNAVAILABLE")
                    exchanges[iid] = instrument.exchange
                row.current_stage, row.progress = "TRAINING", 20
                await self.db.commit()
                evaluation = await asyncio.to_thread(
                    train_kernel, config, dataset.rows, readiness, exchanges
                )
                financial = await asyncio.to_thread(
                    financial_evaluation, dataset, evaluation, config.horizon
                )
                row = await self.db.get(MLTrainingRun, run_id, populate_existing=True)
                assert row is not None
                if row.status != "RUNNING":
                    return None
                row.current_stage, row.progress = "ARTIFACTS", 90
                artifacts = evaluation.pop("artifacts")
                artifact = {
                    "contract": "internal-data-only-model-v1",
                    "training_code": config_data["code"],
                    "dataset_hash": dataset.content_hash,
                    "configuration": config_data["request"],
                    "fold_models": artifacts,
                }
                data = json.dumps(
                    artifact, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
                sha = hashlib.sha256(data).hexdigest()
                key = f"model-artifacts/{run_id}/{sha}.json"
                storage = get_storage()
                await asyncio.to_thread(storage.ensure_bucket)
                if await asyncio.to_thread(storage.exists, key):
                    if hashlib.sha256(await asyncio.to_thread(storage.get, key)).hexdigest() != sha:
                        raise ValueError("ARTIFACT_HASH_MISMATCH")
                else:
                    await asyncio.to_thread(storage.put, key, data, "application/json")
                folds = evaluation["folds"]
                classification = config.model_type in CLASSIFIERS
                metric = "brier" if classification else "rmse"
                losses = [f["test_metrics"][metric] for f in folds]
                baseline_passed = all(
                    f["test_metrics"][metric]
                    < min(m[metric] for m in f["baselines"].values()) * 0.98
                    for f in folds
                )
                evidence = {
                    "production_data_eligible": readiness["production_data_eligible"],
                    "synthetic_evidence": readiness["synthetic_evidence"],
                    "training_observations": min(f["sample_sizes"]["training"] for f in folds),
                    "oos_observations": evaluation["aggregated_oos"]["sample_size"],
                    "oos_signal_dates": evaluation["oos_distinct_dates"],
                    "folds": len(folds),
                    "leakage_verified": True,
                    "baseline_passed": baseline_passed,
                    "calibration_passed": not classification
                    or all(
                        f["calibration"]["status"] == "AVAILABLE"
                        and f["calibration_distinct_dates"] >= config.horizon * 10
                        and f["test_metrics"]["ece"] <= 0.05
                        for f in folds
                    ),
                    "interval_passed": classification
                    or all(
                        f["interval"]["status"] == "AVAILABLE"
                        and 0.75 <= f["interval"].get("empirical_oos_coverage", 0) <= 0.95
                        for f in folds
                    ),
                    "stability_passed": min(losses) > 0 and max(losses) / min(losses) <= 2,
                    "financial_backtest_passed": financial["passed"],
                    "model_card_verified": False,
                    "artifact_verified": True,
                    "code_verified": config_data["code"]["git_commit"] != "UNVERIFIED",
                }
                evaluation.update(
                    {
                        "readiness": readiness,
                        "promotion_evidence": evidence,
                        "promotion_reasons": promotion_reasons(evidence),
                        "financial_status": "EVALUATED",
                        "financial": financial,
                    }
                )
                model_id = uuid4()
                try:
                    mlflow_run_id = await asyncio.to_thread(
                        track_model,
                        str(model_id),
                        config_data["request"],
                        evaluation["aggregated_oos"],
                        key,
                        sha,
                        data,
                    )
                    evaluation["tracking_status"] = (
                        "AVAILABLE" if mlflow_run_id else "NOT_CONFIGURED"
                    )
                except Exception:
                    mlflow_run_id = None
                    evaluation["tracking_status"] = "MLFLOW_UNAVAILABLE"
                model = MLModelVersion(
                    created_at=datetime.now(UTC),
                    id=model_id,
                    mlflow_run_id=mlflow_run_id,
                    user_id=owner_id,
                    training_run_id=run_id,
                    dataset_id=config.dataset_id,
                    model_type=config.model_type,
                    target_type=config.target,
                    horizon=config.horizon,
                    configuration=config_data,
                    evaluation=evaluation,
                    artifact_key=key,
                    artifact_hash=sha,
                    content_hash=digest(
                        {
                            "configuration": config_data,
                            "evaluation": evaluation,
                            "artifact_hash": sha,
                        }
                    ),
                )
                self.db.add(model)
                await self.db.flush()
                self.db.add(
                    ModelPromotionReview(
                        created_at=datetime.now(UTC),
                        model_id=model.id,
                        reviewer_id=owner_id,
                        status="SHADOW",
                        evidence={
                            "origin": "INITIAL_EVALUATION",
                            "reasons": evaluation["promotion_reasons"],
                        },
                    )
                )
                row.status, row.current_stage, row.progress, row.completed_at = (
                    "COMPLETED",
                    "COMPLETED",
                    100,
                    datetime.now(UTC),
                )
                await self.db.commit()
                return model
        except Exception as error:
            await self.db.rollback()
            row = await self.db.get(MLTrainingRun, run_id)
            if row is not None and row.status != "CANCELLED":
                # Only known constant error codes are exposed. Provider details,
                # exception strings and credentials never enter the job log.
                code = (
                    str(error)
                    if isinstance(error, ValueError)
                    else "TRAINING_TIMEOUT"
                    if isinstance(error, TimeoutError)
                    else "TRAINING_FAILED"
                )
                row.error_code = code if code.isupper() and len(code) <= 80 else "TRAINING_FAILED"
                row.status, row.completed_at = "FAILED", datetime.now(UTC)
                await self.db.commit()
            return None
