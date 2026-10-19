from datetime import UTC, date, datetime
from math import isfinite
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.validation import available
from app.core.errors import AppError
from app.ml.calibration import calibrated
from app.ml.explanations import explain
from app.ml.models import predict_estimator, transform
from app.ml.training import feature_matrix
from app.models import (
    Instrument,
    MLModelVersion,
    Prediction,
    PredictionOutcome,
    UniverseMembershipVersion,
)
from app.schemas.pit import DatasetInput
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.ml_registry import ModelRegistryService
from app.services.pit_datasets import DatasetBuilder
from app.services.pit_evidence import EvidenceService
from app.services.pit_features import FeatureSnapshotService


class PredictionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self,
        instrument_id: UUID,
        horizon: int,
        user_id: UUID,
        *,
        shadow_model_ids: tuple[UUID, UUID] | None = None,
        forward_key: str | None = None,
        forward_source_policy: list[dict[str, str]] | None = None,
    ) -> Prediction:
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        now = datetime.now(UTC)
        registry = ModelRegistryService(self.db)
        candidates = (
            await self.db.scalars(
                select(MLModelVersion)
                .where(MLModelVersion.user_id == user_id, MLModelVersion.horizon == horizon)
                .order_by(MLModelVersion.created_at.desc())
                .limit(100)
            )
        ).all()
        production = [m for m in candidates if await registry.status(m.id) == "PRODUCTION"]
        if shadow_model_ids:
            # Only the operator-controlled PR2 service calls this internal path.
            # Inference still traverses the same membership/features/artifact and
            # calibration checks; no production status is created.
            from app.schemas.validation import SourcePolicy
            from app.services.real_data_readiness import dataset_origins, source_preconditions

            policies = await source_preconditions(
                self.db, [SourcePolicy.model_validate(p) for p in forward_source_policy or []]
            )
            allowed_sources = {(p["source_id"], p["use"]) for p in policies if not p["gate_reason"]}

            production = []
            for mid in shadow_model_ids:
                model = await registry.owned(mid, user_id)
                if model.horizon != horizon or await registry.status(mid) != "SHADOW":
                    raise AppError(
                        422, "SHADOW_MODEL_REQUIRED", "Explicit current SHADOW model required"
                    )
                dataset = await DatasetBuilder(self.db).owned(model.dataset_id, user_id)
                await DatasetBuilder(self.db).rebuild(dataset.id, user_id)
                origins = await dataset_origins(self.db, dataset, user_id)
                if (
                    not {(s["source_id"], s["use"]) for s in origins["required_sources"]}
                    <= allowed_sources
                ):
                    raise AppError(
                        403, "PINNED_SOURCE_OUTSIDE_POLICY", "Forward policy excludes pinned inputs"
                    )
                if (
                    not origins["all_real"]
                    or not model.evaluation.get("promotion_evidence", {}).get(
                        "production_data_eligible"
                    )
                    or model.evaluation.get("promotion_evidence", {}).get("synthetic_evidence")
                    is not False
                ):
                    raise AppError(
                        422,
                        "REAL_SHADOW_EVIDENCE_REQUIRED",
                        "Real strict data is required for forward research",
                    )
                production.append(model)
        classifier = next((m for m in production if m.target_type == "classification"), None)
        regressor = next(
            (
                m
                for m in production
                if m.target_type == "excess_return"
                and classifier
                and m.dataset_id == classifier.dataset_id
            ),
            None,
        )
        result: dict[str, Any] = {
            "confidence_status": "NO RELIABLE FORECAST",
            "reason": "Insufficient verified historical data",
            "input_quality": {"status": "NOT_EVALUATED"},
            "probability_outperform": None,
            "expected_return": None,
            "expected_excess_return": None,
            "expected_volatility": None,
            "lower_bound": None,
            "upper_bound": None,
            "requested_horizon": horizon,
            "instrument_id": str(instrument_id),
            "generated_at": now.isoformat(),
        }
        snapshot_id, model_id, dataset_id = None, None, None
        if classifier and regressor:
            dataset_id, model_id = classifier.dataset_id, classifier.id
            dataset = await DatasetBuilder(self.db).owned(dataset_id, user_id)
            try:
                # Limit application to the explicitly validated historical universe.
                if str(instrument_id) not in {
                    r["instrument_id"] for r in dataset.rows if r["eligible"]
                }:
                    raise ValueError("INSTRUMENT_OUTSIDE_VALIDATED_UNIVERSE")
                evidence = EvidenceService(self.db)
                universe_review = await evidence.latest("universe", dataset.universe_id, now)
                if (
                    not universe_review
                    or not universe_review.level.startswith("VERIFIED_")
                    or universe_review.evidence.get("includes_delisted") is not True
                    or not universe_review.evidence.get("valid_from", "9999")
                    <= now.date().isoformat()
                    <= universe_review.evidence.get("valid_to", "0000")
                ):
                    raise ValueError("CURRENT_UNIVERSE_COVERAGE_UNVERIFIED")
                versions = (
                    await self.db.scalars(
                        select(UniverseMembershipVersion)
                        .where(
                            UniverseMembershipVersion.universe_id == dataset.universe_id,
                            UniverseMembershipVersion.instrument_id == instrument_id,
                            UniverseMembershipVersion.known_at <= now,
                            UniverseMembershipVersion.observed_at <= now,
                        )
                        .order_by(UniverseMembershipVersion.observed_at.desc())
                    )
                ).all()
                latest: dict[date, UniverseMembershipVersion] = {}
                for membership in versions:
                    latest.setdefault(membership.valid_from, membership)
                active = [
                    m
                    for m in latest.values()
                    if m.valid_from <= now.date()
                    and (m.valid_to is None or now.date() <= m.valid_to)
                ]
                exits = [
                    m.valid_from for m in active if m.membership_status in {"REMOVED", "DELISTED"}
                ]
                listed = [
                    m
                    for m in active
                    if m.membership_status == "LISTED" and (not exits or m.valid_from > max(exits))
                ]
                if len(listed) != 1:
                    raise ValueError("CURRENT_MEMBERSHIP_UNVERIFIED")
                membership = listed[0]
                review = await evidence.latest("membership", membership.id, now)
                if not review or not available(
                    "STRICT_PIT",
                    now,
                    membership.known_at,
                    membership.observed_at,
                    review.level,
                    review.created_at,
                ):
                    raise ValueError("CURRENT_MEMBERSHIP_UNVERIFIED")
                snapshot = await FeatureSnapshotService(self.db).build(
                    instrument_id, now, "STRICT_PIT", UUID(dataset.configuration["benchmark_id"])
                )
                snapshot_id = snapshot.id
                result["input_quality"] = snapshot.result["quality"]
                if not snapshot.result["quality"].get("action_coverage"):
                    raise ValueError("CORPORATE_ACTION_COVERAGE_UNVERIFIED")
                values = {}
                explanations = []
                interval = None
                output_models = [
                    ("probability_outperform", classifier),
                    ("expected_excess_return", regressor),
                ]
                for name, target_type in (
                    ("expected_return", "instrument_return"),
                    ("expected_volatility", "realized_volatility"),
                ):
                    optional = next(
                        (
                            m
                            for m in production
                            if m.target_type == target_type and m.dataset_id == dataset_id
                        ),
                        None,
                    )
                    if optional:
                        output_models.append((name, optional))
                for name, model in output_models:
                    artifact = await registry.artifact(model)
                    if (
                        datetime.fromisoformat(
                            model.configuration["request"]["folds"][-1]["final_end"]
                        )
                        > now
                    ):
                        raise ValueError("MODEL_KNOWLEDGE_IN_FUTURE")
                    fitted = artifact["fold_models"][-1]
                    names = fitted["preprocessor"]["names"]
                    from app.ml.readiness import finite_feature

                    if any(
                        snapshot.result["features"].get(name, {}).get("missing_flag", True)
                        or not finite_feature(
                            snapshot.result["features"].get(name, {}).get("value")
                        )
                        for name in model.configuration["request"]["required_features"]
                    ):
                        raise ValueError("MISSING_CRITICAL_FINANCIAL_FEATURE")
                    x = transform(
                        feature_matrix([{"features": snapshot.result["features"]}], names),
                        fitted["preprocessor"],
                    )
                    value = predict_estimator(fitted["estimator"], x)
                    if name == "probability_outperform":
                        value = calibrated(value, fitted["calibrator"])
                        calibrated_bin = min(9, int(float(value[0]) * 10))
                        supported = next(
                            (
                                b
                                for b in model.evaluation["folds"][-1]["test_metrics"][
                                    "calibration_curve"
                                ]
                                if b["bin"] == calibrated_bin
                                and b["count"] >= 50
                                and abs(b["observed"] - b["predicted"]) <= 0.05
                            ),
                            None,
                        )
                        if supported is None:
                            raise ValueError("CALIBRATION_SUPPORT_INSUFFICIENT")
                    elif name == "expected_excess_return":
                        interval = fitted["interval"]
                        if interval["status"] != "AVAILABLE":
                            raise ValueError("INTERVAL_UNAVAILABLE")
                    values[name] = float(value[0])
                    if (
                        not isfinite(values[name])
                        or (name == "probability_outperform" and not 0 <= values[name] <= 1)
                        or (name == "expected_return" and values[name] < -1)
                        or (name == "expected_volatility" and values[name] < 0)
                    ):
                        raise ValueError("MODEL_OUTPUT_INVALID")
                    estimator = fitted["estimator"]
                    explanations.append(
                        {
                            **explain(estimator, x, fitted["preprocessor"]),
                            "model_id": str(model.id),
                            "feature_snapshot_id": str(snapshot.id),
                            "feature_values": {n: snapshot.result["features"][n] for n in names},
                        }
                    )
                assert interval is not None
                result.update(
                    {
                        **values,
                        "confidence_status": "VALIDATED",
                        "reason": None,
                        "lower_bound": values["expected_excess_return"] - interval["radius"],
                        "upper_bound": values["expected_excess_return"] + interval["radius"],
                        "interval_level": interval["interval_level"],
                        "uncertainty_method": interval["method"],
                        "empirical_coverage": regressor.evaluation["folds"][-1]["interval"][
                            "empirical_oos_coverage"
                        ],
                        "model_versions": [str(m.id) for _, m in output_models],
                        "explanations": explanations,
                        "target_configuration": dataset.configuration,
                        "signal_day": now.date().isoformat(),
                    }
                )
            except Exception as error:
                code = (
                    error.code
                    if isinstance(error, AppError)
                    else str(error)
                    if isinstance(error, ValueError)
                    else "INFERENCE_FAILED"
                )
                result["reason"] = (
                    code if code.isupper() and len(code) <= 80 else "INFERENCE_FAILED"
                )
        if shadow_model_ids:
            result.update(
                {
                    "archive_kind": "FORWARD_ARCHIVED_SHADOW",
                    "forward_key": forward_key,
                    "forward_source_policy": forward_source_policy,
                    "confidence_status": "EXPERIMENTAL_SHADOW"
                    if result["confidence_status"] == "VALIDATED"
                    else "ABSTAINED",
                    "investment_use": "NOT_VALIDATED_NO_RECOMMENDATIONS",
                }
            )
            calendar = MarketCalendarService()
            signal_day = now.date()
            if instrument.exchange:
                if not calendar.is_session(instrument.exchange, signal_day):
                    signal_day = calendar.previous_session(instrument.exchange, signal_day)
                result["target_calendar"] = {
                    "exchange": instrument.exchange,
                    "version": calendar.version,
                    "signal_day": signal_day.isoformat(),
                    "label_start": calendar.session_open(
                        instrument.exchange, calendar.next_session(instrument.exchange, signal_day)
                    ).isoformat(),
                    "label_end": calendar.session_close(
                        instrument.exchange,
                        calendar.horizon(instrument.exchange, signal_day, horizon),
                    ).isoformat(),
                }
        row = Prediction(
            user_id=user_id,
            instrument_id=instrument_id,
            model_id=model_id,
            dataset_id=dataset_id,
            feature_snapshot_id=snapshot_id,
            horizon=horizon,
            generated_at=now,
            information_cutoff_at=now,
            result=result,
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def outcome(self, prediction_id: UUID, user_id: UUID) -> PredictionOutcome | None:
        prediction = await self.db.get(Prediction, prediction_id)
        if prediction is None or prediction.user_id != user_id:
            raise AppError(404, "PREDICTION_NOT_FOUND", "Prediction not found")
        if prediction.result["confidence_status"] != "VALIDATED" and not (
            prediction.result.get("archive_kind") == "FORWARD_ARCHIVED_SHADOW"
            and prediction.result["confidence_status"] == "EXPERIMENTAL_SHADOW"
        ):
            return None
        config_data = prediction.result["target_configuration"]
        if prediction.result.get("archive_kind") == "FORWARD_ARCHIVED_SHADOW":
            from app.schemas.validation import SourcePolicy
            from app.services.real_data_readiness import source_preconditions

            policies = prediction.result.get("forward_source_policy")
            if not policies or any(
                p["gate_reason"]
                for p in await source_preconditions(
                    self.db, [SourcePolicy.model_validate(p) for p in policies]
                )
            ):
                return None
        config = DatasetInput.model_validate(
            {k: v for k, v in config_data.items() if k in DatasetInput.model_fields}
        )
        instrument = await self.db.get(Instrument, prediction.instrument_id)
        assert instrument and instrument.exchange
        calendar = MarketCalendarService()
        pinned_calendar = prediction.result.get("target_calendar")
        if pinned_calendar and (
            pinned_calendar["exchange"] != instrument.exchange
            or pinned_calendar["version"] != calendar.version
        ):
            return None
        day = date.fromisoformat(prediction.result["signal_day"])
        if not calendar.is_session(instrument.exchange, day):
            day = calendar.previous_session(instrument.exchange, day)
        target = await DatasetBuilder(self.db).target(
            prediction.instrument_id, config.benchmark_id, day, prediction.generated_at, config
        )
        if pinned_calendar and any(
            target[key] != pinned_calendar[key] for key in ("label_start", "label_end")
        ):
            return None
        if target["status"] != "AVAILABLE" or datetime.fromisoformat(
            target["label_available_at"]
        ) > datetime.now(UTC):
            return None
        result = {
            "target": target,
            "actual_instrument_return": target["instrument_return"],
            "actual_benchmark_return": target["benchmark_return"],
            "actual_excess_return": target["excess_return"],
            "correct": (prediction.result["probability_outperform"] >= 0.5)
            == bool(target["classification"]),
        }
        content = digest(result)
        previous = await self.db.scalar(
            select(PredictionOutcome)
            .where(PredictionOutcome.prediction_id == prediction_id)
            .order_by(PredictionOutcome.created_at.desc())
            .limit(1)
        )
        if previous and previous.content_hash == content:
            return previous
        row = PredictionOutcome(
            prediction_id=prediction_id,
            replaces_id=previous.id if previous else None,
            content_hash=content,
            result={**result, "evaluated_at": datetime.now(UTC).isoformat()},
        )
        self.db.add(row)
        await self.db.commit()
        return row
