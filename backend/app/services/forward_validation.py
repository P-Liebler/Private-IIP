"""Forward research uses the existing immutable prediction/outcome registry."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.metrics import classification_metrics, regression_metrics
from app.models import Instrument, Prediction, PredictionOutcome, User, ValidationRecord
from app.schemas.validation import ForwardInput
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.ml_registry import ModelRegistryService
from app.services.ml_training import require_ml_operator
from app.services.predictions import PredictionService
from app.services.real_data_readiness import source_preconditions
from app.services.validation_records import ValidationRecords
from app.services.work_limits import work_slot


class ForwardValidationService:
    def __init__(self, db: AsyncSession, user: User):
        self.db, self.user = db, user
        self.user_id = user.id
        self.records = ValidationRecords(db, user.id)

    async def policies(self) -> list[dict[str, Any]]:
        policies = []
        for policy in await self.records.list("FORWARD_POLICY", 100):
            state = await self.db.scalar(
                select(ValidationRecord)
                .where(
                    ValidationRecord.parent_id == policy.id,
                    ValidationRecord.kind == "FORWARD_POLICY_STATE",
                )
                .order_by(ValidationRecord.created_at.desc(), ValidationRecord.id.desc())
                .limit(1)
            )
            policies.append(
                {
                    "id": str(policy.id),
                    "horizon": policy.result["horizon"],
                    "enabled": state.result["enabled"]
                    if state
                    else policy.request["scheduling_enabled"],
                }
            )
        return policies

    async def register(self, request: ForwardInput) -> ValidationRecord:
        require_ml_operator(self.user)
        if len(await self.records.list("FORWARD_POLICY", 100)) >= 100:
            raise AppError(429, "FORWARD_POLICY_LIMIT", "At most 100 versioned policies per user")
        registry = ModelRegistryService(self.db)
        classifier = await registry.owned(request.classifier_id, self.user_id)
        regressor = await registry.owned(request.regressor_id, self.user_id)
        if (
            classifier.target_type != "classification"
            or regressor.target_type != "excess_return"
            or classifier.dataset_id != regressor.dataset_id
            or classifier.horizon != regressor.horizon
        ):
            raise AppError(
                422, "MODEL_PAIR_MISMATCH", "Same-dataset classification/excess pair required"
            )
        for model in (classifier, regressor):
            if await registry.status(model.id) != "SHADOW":
                raise AppError(422, "SHADOW_MODEL_REQUIRED", "Explicit SHADOW candidates required")
        for iid in request.instrument_ids:
            if await self.db.get(Instrument, iid) is None:
                raise AppError(404, "INSTRUMENT_NOT_FOUND", "Existing instrument required")
        return await self.records.append(
            "FORWARD_POLICY",
            request.model_dump(mode="json"),
            {
                "horizon": classifier.horizon,
                "archive_kind": "FORWARD_ARCHIVED_SHADOW",
                "status": "EXPERIMENTAL",
                "generated_at": "ACTUAL_SERVER_TIME_ONLY",
                "outcome_policy": "P6 sessions/prices/actions/FX/benchmark; immutable P7 outcomes",
                "promotion": "NONE",
            },
        )

    async def scheduling(self, identifier: UUID, enabled: bool) -> ValidationRecord:
        require_ml_operator(self.user)
        await self.records.owned(identifier, "FORWARD_POLICY")
        return await self.records.append(
            "FORWARD_POLICY_STATE",
            {"enabled": enabled},
            {
                "status": "SCHEDULING_ENABLED" if enabled else "SCHEDULING_DISABLED",
                "enabled": enabled,
            },
            parent_id=identifier,
        )

    async def run(self, identifier: UUID) -> ValidationRecord:
        require_ml_operator(self.user)
        policy = await self.records.owned(identifier, "FORWARD_POLICY")
        request = ForwardInput.model_validate(policy.request)
        horizon = policy.result["horizon"]
        results = []
        async with work_slot(917012):
            sources = await source_preconditions(self.db, request.source_policy)
            for iid in request.instrument_ids:
                instrument = await self.db.get(Instrument, iid)
                now = datetime.now(UTC)
                session = now.date().isoformat()
                try:
                    if instrument and instrument.exchange:
                        calendar = MarketCalendarService()
                        day = now.date()
                        if (
                            not calendar.is_session(instrument.exchange, day)
                            or calendar.session_close(instrument.exchange, day)
                            + timedelta(minutes=90)
                            > now
                        ):
                            day = calendar.previous_session(instrument.exchange, day)
                        session = day.isoformat()
                except (ValueError, AppError):
                    pass
                key = digest(
                    {"policy": str(identifier), "instrument": str(iid), "session": session}
                )
                previous = await self.db.scalar(
                    select(Prediction).where(
                        Prediction.user_id == self.user_id,
                        Prediction.result["forward_key"].astext == key,
                    )
                )
                if previous:
                    prediction = previous
                else:
                    try:
                        if any(s["gate_reason"] for s in sources):
                            raise AppError(
                                403, "SOURCE_NOT_APPROVED", "Forward source policy blocked"
                            )
                        prediction = await PredictionService(self.db).generate(
                            iid,
                            horizon,
                            self.user_id,
                            shadow_model_ids=(request.classifier_id, request.regressor_id),
                            forward_key=key,
                            forward_source_policy=[p.model_dump() for p in request.source_policy],
                        )
                    except AppError as error:
                        prediction = Prediction(
                            user_id=self.user_id,
                            instrument_id=iid,
                            horizon=horizon,
                            generated_at=now,
                            information_cutoff_at=now,
                            result={
                                "archive_kind": "FORWARD_ARCHIVED_SHADOW",
                                "confidence_status": "ABSTAINED",
                                "reason": error.code,
                                "forward_key": key,
                                "probability_outperform": None,
                                "expected_excess_return": None,
                                "model_versions": [
                                    str(request.classifier_id),
                                    str(request.regressor_id),
                                ],
                                "generated_at": now.isoformat(),
                            },
                        )
                        self.db.add(prediction)
                        await self.db.commit()
                results.append(
                    {
                        "prediction_id": str(prediction.id),
                        "instrument_id": str(iid),
                        "generated_at": prediction.generated_at.isoformat(),
                        "status": prediction.result["confidence_status"],
                        "reason": prediction.result.get("reason"),
                    }
                )
            return await self.records.append(
                "FORWARD_RUN",
                {},
                {"status": "RECORDED", "predictions": results, "sources": sources},
                parent_id=identifier,
                dedup_key=digest({"policy": str(identifier), "predictions": results}),
            )

    async def outcomes(self) -> ValidationRecord:
        require_ml_operator(self.user)
        checks = await self.records.list("FORWARD_OUTCOME_CHECK", 1)
        cursor = checks[0].result.get("next_cursor") if checks else None
        query = select(Prediction)
        if cursor:
            moment = datetime.fromisoformat(cursor["generated_at"])
            query = query.where(
                or_(
                    Prediction.generated_at > moment,
                    (Prediction.generated_at == moment) & (Prediction.id > UUID(cursor["id"])),
                )
            )

        async def page(statement: Any) -> list[Prediction]:
            return list(
                (
                    await self.db.scalars(
                        statement.where(
                            Prediction.user_id == self.user_id,
                            Prediction.result["archive_kind"].astext == "FORWARD_ARCHIVED_SHADOW",
                            Prediction.result["confidence_status"].astext == "EXPERIMENTAL_SHADOW",
                        )
                        .order_by(Prediction.generated_at, Prediction.id)
                        .limit(10)
                    )
                ).all()
            )

        predictions = await page(query)
        if not predictions and cursor:
            predictions = await page(select(Prediction))
        next_cursor = (
            {
                "generated_at": predictions[-1].generated_at.isoformat(),
                "id": str(predictions[-1].id),
            }
            if predictions
            else None
        )
        evaluated: list[str] = []
        pending: list[str] = []
        prediction_ids = [p.id for p in predictions]
        for prediction_id in prediction_ids:
            try:
                outcome = await PredictionService(self.db).outcome(prediction_id, self.user_id)
                (evaluated if outcome else pending).append(str(prediction_id))
            except AppError:
                # Preserve every historical forecast on source/data outage.
                await self.db.rollback()
                pending.append(str(prediction_id))
        return await self.records.append(
            "FORWARD_OUTCOME_CHECK",
            {},
            {
                "evaluated": evaluated,
                "pending": pending,
                "next_cursor": next_cursor,
                "checked_at": datetime.now(UTC).isoformat(),
            },
        )

    async def report(self, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        confidence_status = Prediction.result["confidence_status"].astext
        totals = (
            await self.db.execute(
                select(Prediction.horizon, confidence_status, func.count())
                .where(
                    Prediction.user_id == self.user_id,
                    Prediction.result["archive_kind"].astext == "FORWARD_ARCHIVED_SHADOW",
                )
                .group_by(Prediction.horizon, confidence_status)
            )
        ).all()
        matured_rows = (
            await self.db.execute(
                select(Prediction.horizon, func.count(func.distinct(Prediction.id)))
                .join(PredictionOutcome, PredictionOutcome.prediction_id == Prediction.id)
                .where(
                    Prediction.user_id == self.user_id,
                    Prediction.result["archive_kind"].astext == "FORWARD_ARCHIVED_SHADOW",
                )
                .group_by(Prediction.horizon)
            )
        ).all()
        matured_counts: dict[int, int] = {int(h): int(n) for h, n in matured_rows}
        predictions = (
            await self.db.scalars(
                select(Prediction)
                .where(
                    Prediction.user_id == self.user_id,
                    Prediction.result["archive_kind"].astext == "FORWARD_ARCHIVED_SHADOW",
                )
                .order_by(Prediction.generated_at.desc(), Prediction.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        statistical_predictions: list[Prediction] = []
        for horizon in (30, 90):
            statistical_predictions.extend(
                (
                    await self.db.scalars(
                        select(Prediction)
                        .where(
                            Prediction.user_id == self.user_id,
                            Prediction.horizon == horizon,
                            Prediction.result["archive_kind"].astext == "FORWARD_ARCHIVED_SHADOW",
                            select(PredictionOutcome.id)
                            .where(PredictionOutcome.prediction_id == Prediction.id)
                            .exists(),
                        )
                        .order_by(Prediction.generated_at.desc(), Prediction.id.desc())
                        .limit(500)
                    )
                ).all()
            )
        outcomes = (
            await self.db.scalars(
                select(PredictionOutcome)
                .where(
                    PredictionOutcome.prediction_id.in_(
                        [p.id for p in [*predictions, *statistical_predictions]]
                    )
                )
                .order_by(PredictionOutcome.created_at.desc(), PredictionOutcome.id.desc())
            )
        ).all()
        latest: dict[UUID, PredictionOutcome] = {}
        for outcome in outcomes:
            latest.setdefault(outcome.prediction_id, outcome)
        groups = []
        for horizon in (30, 90):
            rows = [p for p in statistical_predictions if p.horizon == horizon]
            matured = [p for p in rows if p.id in latest]
            dates = {p.generated_at.date() for p in matured}
            metrics: dict[str, Any] | None = None
            drift: dict[str, Any] = {"status": "INSUFFICIENT_COMPARABLE_WINDOWS"}
            if len(dates) >= 50:
                y = np.asarray([latest[p.id].result["target"]["classification"] for p in matured])
                probabilities = np.asarray([p.result["probability_outperform"] for p in matured])
                target = np.asarray(
                    [float(latest[p.id].result["actual_excess_return"]) for p in matured]
                )
                forecast = np.asarray([p.result["expected_excess_return"] for p in matured])
                metrics = {
                    "classification": classification_metrics(y, probabilities),
                    "regression": regression_metrics(target, forecast),
                }
                bounded = [
                    p
                    for p in matured
                    if p.result.get("lower_bound") is not None
                    and p.result.get("upper_bound") is not None
                ]
                metrics["interval_coverage"] = {
                    "sample_size": len(bounded),
                    "empirical_coverage": sum(
                        float(p.result["lower_bound"])
                        <= float(latest[p.id].result["actual_excess_return"])
                        <= float(p.result["upper_bound"])
                        for p in bounded
                    )
                    / len(bounded)
                    if bounded
                    else None,
                }
                metrics["dependence"] = (
                    "Date-clustered correlated observations; no independence guarantee"
                )
            if len(dates) >= 100:
                ordered = sorted(dates)
                old_dates, new_dates = set(ordered[-100:-50]), set(ordered[-50:])
                old = [p for p in matured if p.generated_at.date() in old_dates]
                new = [p for p in matured if p.generated_at.date() in new_dates]

                def window_metrics(values: list[Prediction]) -> dict[str, Any]:
                    y = np.asarray(
                        [latest[p.id].result["target"]["classification"] for p in values]
                    )
                    probability = np.asarray([p.result["probability_outperform"] for p in values])
                    return {
                        "mean_probability": float(probability.mean()),
                        **classification_metrics(y, probability),
                    }

                prior, recent = window_metrics(old), window_metrics(new)
                shifted = (
                    abs(prior["mean_probability"] - recent["mean_probability"]) >= 0.15
                    or recent["ece"] > 0.10
                    or (prior["brier"] > 0 and recent["brier"] > 2 * prior["brier"])
                )
                drift = {
                    "status": "RESEARCH_DRIFT_DETECTED"
                    if shifted
                    else "NO_THRESHOLD_CROSSING_OBSERVED",
                    "rule_version": "forward-50-date-windows-v1",
                    "prior": prior,
                    "recent": recent,
                    "distinct_dates_per_window": 50,
                    "promotion_effect": "NONE; experimental monitoring only",
                }
            groups.append(
                {
                    "horizon": horizon,
                    "stored": sum(n for h, status, n in totals if h == horizon),
                    "matured": matured_counts.get(horizon, 0),
                    "pending": sum(
                        n
                        for h, status, n in totals
                        if h == horizon and status == "EXPERIMENTAL_SHADOW"
                    )
                    - matured_counts.get(horizon, 0),
                    "abstentions": sum(
                        n for h, status, n in totals if h == horizon and status == "ABSTAINED"
                    ),
                    "metrics_sample_size": len(matured),
                    "distinct_matured_dates": len(dates),
                    "metrics": metrics,
                    "calibration_status": "OBSERVED_EXPERIMENTAL"
                    if metrics
                    else "INSUFFICIENT_MATURED_HISTORY",
                    "drift_status": drift["status"],
                    "drift": drift,
                }
            )
        return {
            "archive_kind": "FORWARD_ARCHIVED_SHADOW",
            "investment_use": "NOT_VALIDATED",
            "groups": groups,
            "history_limit": limit,
            "history_offset": offset,
            "statistical_limit_per_horizon": 500,
            "predictions": [
                {
                    "id": str(p.id),
                    "instrument_id": str(p.instrument_id),
                    "horizon": p.horizon,
                    "model_id": str(p.model_id) if p.model_id else None,
                    "dataset_id": str(p.dataset_id) if p.dataset_id else None,
                    "feature_snapshot_id": str(p.feature_snapshot_id)
                    if p.feature_snapshot_id
                    else None,
                    "generated_at": p.generated_at.isoformat(),
                    "information_cutoff_at": p.information_cutoff_at.isoformat(),
                    "result": p.result,
                    "outcome": latest[p.id].result if p.id in latest else None,
                }
                for p in predictions
            ],
        }
