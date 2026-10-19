"""Immutable pre-registration around the existing P7 queue and P9 replay."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.models import model_parameters
from app.ml.promotion import PROMOTION_RULES, promotion_reasons
from app.ml.regimes import evaluate_regimes
from app.ml.training import TrainingInput
from app.models import DatasetVersion, MLModelVersion, MLTrainingRun, User, ValidationRecord
from app.schemas.recommendations import StrategyBacktestInput
from app.schemas.validation import ExperimentInput, ReadinessInput, SourcePolicy
from app.services.fundamentals import digest
from app.services.ml_registry import ModelRegistryService
from app.services.ml_training import ModelTrainingService, require_ml_operator
from app.services.pit_datasets import DatasetBuilder, code_manifest
from app.services.real_data_readiness import RealDataReadinessService
from app.services.validation_records import ValidationRecords
from app.services.work_limits import work_slot


class ValidationExperimentService:
    def __init__(self, db: AsyncSession, user: User):
        self.db, self.user = db, user
        self.records = ValidationRecords(db, user.id)

    async def audits(self, request: ExperimentInput) -> list[dict[str, Any]]:
        cache: dict[str, dict[str, Any]] = {}
        results = []
        for candidate in request.candidates:
            key = digest(
                candidate.model_dump(
                    mode="json", include={"dataset_id", "horizon", "required_features", "folds"}
                )
            )
            if key not in cache:
                cache[key] = await self.audit_candidate(candidate, request.source_policy)
            results.append(cache[key])
        return results

    async def audit_candidate(
        self, candidate: TrainingInput, policy: list[SourcePolicy]
    ) -> dict[str, Any]:
        dataset = await DatasetBuilder(self.db).owned(candidate.dataset_id, self.user.id)
        config = dataset.configuration
        return await RealDataReadinessService(self.db, self.user.id).report(
            ReadinessInput(
                universe_id=dataset.universe_id,
                benchmark_id=UUID(config["benchmark_id"]),
                start=config["start"],
                end=config["end"],
                horizon=candidate.horizon,
                availability_mode=config["availability_mode"],
                base_currency=config["base_currency"],
                dataset_id=dataset.id,
                required_features=candidate.required_features,
                folds=candidate.folds,
                source_policy=policy,
            )
        )

    async def register(self, request: ExperimentInput) -> ValidationRecord:
        require_ml_operator(self.user)
        async with work_slot(917011):
            protocols = await self.records.list("EXPERIMENT_PROTOCOL", 1000)
            if len(protocols) >= 1000:
                raise AppError(429, "PROTOCOL_LIMIT", "Protocol reservation capacity reached")
            identifiers = {c.dataset_id for c in request.candidates} | {
                UUID(c["dataset_id"]) for p in protocols for c in p.request["candidates"]
            }
            scope_rows = (
                await self.db.execute(
                    select(DatasetVersion.id, DatasetVersion.universe_id).where(
                        DatasetVersion.user_id == self.user.id, DatasetVersion.id.in_(identifiers)
                    )
                )
            ).all()
            scopes = {identifier: universe for identifier, universe in scope_rows}
            if set(scopes) != identifiers:
                raise AppError(409, "EXPERIMENT_HISTORY_INCOMPLETE", "Dataset history unavailable")
            existing = (
                await self.db.execute(
                    select(MLTrainingRun, DatasetVersion.universe_id)
                    .join(DatasetVersion, DatasetVersion.id == MLTrainingRun.dataset_id)
                    .where(
                        MLTrainingRun.user_id == self.user.id,
                        DatasetVersion.universe_id.in_(
                            {scopes[c.dataset_id] for c in request.candidates}
                        ),
                    )
                )
            ).all()
            for candidate in request.candidates:
                for run, universe in existing:
                    if (
                        universe == scopes[candidate.dataset_id]
                        and run.configuration["request"]["horizon"] == candidate.horizon
                    ):
                        for old in run.configuration["request"]["folds"]:
                            if any(
                                datetime.fromisoformat(old["test_start"]) <= f.final_end
                                and f.test_start <= datetime.fromisoformat(old["final_end"])
                                for f in candidate.folds
                            ):
                                raise AppError(
                                    409,
                                    "OOS_ALREADY_EXPOSED",
                                    "Final test already exposed; select an untouched window",
                                )
                for protocol in protocols:
                    for old in protocol.request["candidates"]:
                        if (
                            scopes[UUID(old["dataset_id"])] == scopes[candidate.dataset_id]
                            and old["horizon"] == candidate.horizon
                        ) and any(
                            datetime.fromisoformat(w["test_start"]) <= f.final_end
                            and f.test_start <= datetime.fromisoformat(w["final_end"])
                            for w in old["folds"]
                            for f in candidate.folds
                        ):
                            raise AppError(
                                409,
                                "OOS_ALREADY_RESERVED",
                                "Final test is reserved by an immutable protocol",
                            )
            audits = await self.audits(request)
            return await self.records.append(
                "EXPERIMENT_PROTOCOL",
                request.model_dump(mode="json"),
                {
                    "archive_kind": "RETROSPECTIVE_PIT_EXPERIMENT",
                    "registered_at": datetime.now(UTC).isoformat(),
                    "status": "PRE_REGISTERED",
                    "promotion_rules": PROMOTION_RULES,
                    "parameter_grid": [
                        {
                            str(k): model_parameters(c.model_type, c.seed, k)
                            for k in c.search_complexities
                        }
                        for c in request.candidates
                    ],
                    "metrics": {
                        "classification": [
                            "Brier",
                            "ECE",
                            "ROC_AUC",
                            "PR_AUC",
                            "Precision",
                            "Recall",
                            "F1",
                            "calibration_curve",
                        ],
                        "regression": ["MAE", "RMSE", "Bias", "Pearson", "Spearman"],
                        "financial": [
                            "Net Excess Return",
                            "CAGR",
                            "Sharpe",
                            "Sortino",
                            "Maximum Drawdown",
                            "Turnover",
                            "Costs",
                        ],
                    },
                    "baselines": [
                        "NO_SKILL",
                        "HISTORICAL_MEAN",
                        "NO_CHANGE",
                        "BENCHMARK_ONLY",
                        "EQUAL_WEIGHT",
                        "MOMENTUM",
                        "QUALITY_VALUE",
                    ],
                    "readiness_at_registration": audits,
                    "regimes": {
                        key: {"definition": value, "status": "REQUIRES_PINNED_REGIME_EVIDENCE"}
                        for key, value in request.regime_definitions.items()
                    },
                    "acceptance": "Existing P7 gates; separate operator review; no promotion",
                },
            )

    async def queue(self, identifier: UUID, index: int) -> ValidationRecord:
        require_ml_operator(self.user)
        protocol = await self.records.owned(identifier, "EXPERIMENT_PROTOCOL")
        if protocol.result["code"] != code_manifest():
            raise AppError(409, "EXPERIMENT_CODE_CHANGED", "Protocol pins different implementation")
        request = ExperimentInput.model_validate(protocol.request)
        if not 0 <= index < len(request.candidates):
            raise AppError(422, "CANDIDATE_INDEX_INVALID", "Select a registered candidate")
        async with work_slot(917011):
            key = digest({"protocol": str(identifier), "candidate": index})
            previous = next(
                (r for r in await self.records.list("EXPERIMENT_RUN", 1000) if r.dedup_key == key),
                None,
            )
            if previous:
                return previous
            candidate = request.candidates[index]
            audit = await self.audit_candidate(candidate, request.source_policy)
            if audit["readiness_status"] != "REAL_DATA_READY":
                return await self.records.append(
                    "EXPERIMENT_BLOCKED",
                    {"candidate_index": index},
                    {"status": "BLOCKED_BY_REAL_DATA", "readiness": audit},
                    parent_id=identifier,
                )
            # Reserve the association before publishing to Celery. P7 commits its
            # durable QUEUED row before broker dispatch; recover a matching run
            # after interruption without silently training a second candidate.
            runs = (
                await self.db.scalars(
                    select(MLTrainingRun).where(
                        MLTrainingRun.user_id == self.user.id,
                        MLTrainingRun.dataset_id == candidate.dataset_id,
                        MLTrainingRun.created_at >= protocol.created_at,
                    )
                )
            ).all()
            run = next(
                (
                    r
                    for r in runs
                    if r.configuration["request"] == candidate.model_dump(mode="json")
                ),
                None,
            )
            if run is None:
                run = await ModelTrainingService(self.db).queue(candidate, self.user)
            return await self.records.append(
                "EXPERIMENT_RUN",
                {"candidate_index": index},
                {
                    "training_run_id": str(run.id),
                    "configuration_hash": digest(candidate.model_dump(mode="json")),
                    "status": "P7_QUEUE_OWNS_EXECUTION",
                },
                parent_id=identifier,
                dedup_key=key,
            )

    async def evaluate(self, identifier: UUID) -> ValidationRecord:
        require_ml_operator(self.user)
        protocol = await self.records.owned(identifier, "EXPERIMENT_PROTOCOL")
        if protocol.result["code"] != code_manifest():
            raise AppError(409, "EXPERIMENT_CODE_CHANGED", "Protocol pins different implementation")
        request = ExperimentInput.model_validate(protocol.request)
        results = []
        registry = ModelRegistryService(self.db)
        links = (
            await self.db.scalars(
                select(ValidationRecord).where(
                    ValidationRecord.user_id == self.user.id,
                    ValidationRecord.kind == "EXPERIMENT_RUN",
                    ValidationRecord.parent_id == identifier,
                )
            )
        ).all()
        for index, candidate in enumerate(request.candidates):
            link = next((r for r in links if r.request["candidate_index"] == index), None)
            if not link:
                results.append({"candidate_index": index, "status": "NOT_RUN", "metrics": None})
                continue
            run = await ModelTrainingService(self.db).owned(
                UUID(link.result["training_run_id"]), self.user.id
            )
            model = await self.db.scalar(
                select(MLModelVersion).where(MLModelVersion.training_run_id == run.id)
            )
            if not model:
                results.append(
                    {
                        "candidate_index": index,
                        "status": run.status,
                        "error_code": run.error_code,
                        "metrics": None,
                    }
                )
                continue
            if run.created_at < protocol.created_at or model.configuration[
                "request"
            ] != candidate.model_dump(mode="json"):
                raise AppError(
                    409, "EXPERIMENT_BINDING_INVALID", "Run differs from pre-registration"
                )
            await registry.artifact(model)
            await DatasetBuilder(self.db).rebuild(model.dataset_id, self.user.id)
            dataset = await DatasetBuilder(self.db).owned(model.dataset_id, self.user.id)
            evaluation = model.evaluation
            results.append(
                {
                    "candidate_index": index,
                    "model_id": str(model.id),
                    "status": await registry.status(model.id),
                    "target": model.target_type,
                    "horizon": model.horizon,
                    "evaluation": evaluation,
                    "promotion_blockers": promotion_reasons(evaluation["promotion_evidence"]),
                    "regime_results": evaluate_regimes(
                        dataset.rows, evaluation, model.target_type, request.regime_rules
                    ),
                    "model_card": {
                        "model_id": str(model.id),
                        "dataset_id": str(model.dataset_id),
                        "feature_set": candidate.feature_names,
                        "periods": [f.model_dump(mode="json") for f in candidate.folds],
                        "artifact_hash": model.artifact_hash,
                        "limitations": "Retrospective; correlated samples; no forward record",
                        "failure_modes": [
                            "SOURCE_OUTAGE",
                            "FEATURE_MISSING",
                            "CALIBRATION_DRIFT",
                            "REGIME_CHANGE",
                        ],
                    },
                }
            )
        audits = await self.audits(request)
        complete = len(results) == len(request.candidates) and all(
            r.get("evaluation") for r in results
        )
        return await self.records.append(
            "EXPERIMENT_EVALUATION",
            {},
            {
                "status": "VALIDATION_COMPLETED"
                if complete and all(a["readiness_status"] == "REAL_DATA_READY" for a in audits)
                else "BLOCKED_BY_REAL_DATA"
                if any(a["readiness_status"] != "REAL_DATA_READY" for a in audits)
                else "VALIDATION_INCOMPLETE",
                "comparisons": results,
                "readiness": audits,
                "selection_policy": "Registered comparison; no OOS tuning",
                "promotion": "NO_AUTOMATIC_PROMOTION",
                "forward_evidence": "SEPARATE_FORWARD_ARCHIVED_SHADOW",
                "regime_robustness": "NOT_ESTABLISHED_WITHOUT_PINNED_REGIME_LABELS",
            },
            parent_id=identifier,
        )

    async def strategy(self, request: StrategyBacktestInput) -> ValidationRecord:
        require_ml_operator(self.user)
        from app.recommendations.backtesting import RecommendationBacktestingService
        from app.services.portfolios import PortfolioService
        from app.services.real_data_readiness import dataset_origins

        await PortfolioService(self.db, self.user.id).owned(request.portfolio_id)

        dataset = await DatasetBuilder(self.db).owned(request.dataset_id, self.user.id)
        await DatasetBuilder(self.db).rebuild(dataset.id, self.user.id)
        origins = await dataset_origins(self.db, dataset, self.user.id)
        if not origins["all_real"]:
            return await self.records.append(
                "STRATEGY_EVALUATION",
                request.model_dump(mode="json"),
                {
                    "status": "BLOCKED_BY_REAL_DATA",
                    "archive_kind": "RESEARCH_BACKTEST",
                    "blocking_reasons": ["REAL_ORIGINAL_EVIDENCE_REQUIRED"],
                    "origins": origins,
                    "metrics": None,
                    "promotion": "V3 RECOMMENDATIONS GATED",
                },
            )
        run = await RecommendationBacktestingService(self.db, self.user.id).run(request)
        return await self.records.append(
            "STRATEGY_EVALUATION",
            request.model_dump(mode="json"),
            {
                "status": "EVALUATED",
                "archive_kind": "ARCHIVED_FORWARD_EVALUATION",
                "backtest_id": str(run.id),
                "content_hash": run.content_hash,
                "result": run.result,
                "promotion": "SEPARATE_EXISTING_P9_OPERATOR_REVIEW_REQUIRED",
            },
        )
