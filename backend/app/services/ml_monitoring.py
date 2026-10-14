import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage
from app.ml.metrics import classification_metrics
from app.models import (
    FeatureSnapshot,
    MLModelVersion,
    ModelPromotionReview,
    Prediction,
    PredictionOutcome,
    PriceDailyVersion,
)
from app.services.ml_registry import ModelRegistryService


class MLMonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def report(self, user_id: UUID) -> dict[str, Any]:
        predictions = (
            await self.db.scalars(
                select(Prediction)
                .where(Prediction.user_id == user_id)
                .order_by(Prediction.created_at.desc())
                .limit(1000)
            )
        ).all()
        outcomes = (
            await self.db.scalars(
                select(PredictionOutcome)
                .where(PredictionOutcome.prediction_id.in_([p.id for p in predictions]))
                .order_by(PredictionOutcome.created_at.desc())
            )
        ).all()
        latest: dict[UUID, PredictionOutcome] = {}
        for outcome in outcomes:
            latest.setdefault(outcome.prediction_id, outcome)
        models = (
            await self.db.scalars(
                select(MLModelVersion).where(MLModelVersion.user_id == user_id).limit(100)
            )
        ).all()
        statuses = []
        for model in models:
            realized = [
                p
                for p in predictions
                if p.model_id == model.id
                and p.id in latest
                and p.result.get("probability_outperform") is not None
            ]
            metrics = (
                classification_metrics(
                    [int(float(latest[p.id].result["actual_excess_return"]) > 0) for p in realized],
                    [p.result["probability_outperform"] for p in realized],
                )
                if len(realized) >= 100
                else None
            )
            status = await ModelRegistryService(self.db).status(model.id)
            degraded = bool(
                metrics
                and (
                    metrics["ece"] > 0.1
                    or metrics["brier"] > model.evaluation["aggregated_oos"].get("brier", 1) + 0.05
                )
            )
            if degraded and status == "PRODUCTION":
                self.db.add(
                    ModelPromotionReview(
                        created_at=datetime.now(UTC),
                        model_id=model.id,
                        reviewer_id=user_id,
                        status="SHADOW",
                        evidence={
                            "origin": "MODEL_DEGRADED",
                            "metrics": metrics,
                            "rule_version": "realized-drift-v1",
                        },
                    )
                )
                status = "SHADOW"
            statuses.append(
                {
                    "model_id": str(model.id),
                    "status": status,
                    "monitoring_status": "MODEL_DEGRADED"
                    if degraded
                    else "INSUFFICIENT_OUTCOMES"
                    if metrics is None
                    else "MONITORED",
                    "realized_outcomes": len(realized),
                    "calibration_drift": metrics,
                }
            )
            try:
                statuses[-1]["artifact_availability"] = (
                    "AVAILABLE"
                    if await asyncio.to_thread(get_storage().exists, model.artifact_key)
                    else "UNAVAILABLE"
                )
            except Exception:
                statuses[-1]["artifact_availability"] = "UNAVAILABLE"
        await self.db.commit()
        observed_quality = [
            p.result["input_quality"]
            for p in predictions
            if p.result.get("input_quality", {}).get("missing_features") is not None
        ]
        snapshot_ids = [p.feature_snapshot_id for p in predictions[:20] if p.feature_snapshot_id]
        snapshots = (
            await self.db.scalars(
                select(FeatureSnapshot).where(FeatureSnapshot.id.in_(snapshot_ids))
            )
        ).all()
        price_ids = {
            UUID(iid)
            for snapshot in snapshots
            for iid in snapshot.result.get("input_version_ids", {}).get("prices", [])
        }
        prices = (
            await self.db.scalars(
                select(PriceDailyVersion).where(PriceDailyVersion.id.in_(price_ids))
            )
        ).all()
        price_dates = {str(p.id): p.trading_date for p in prices}
        ages = [
            (
                datetime.now(UTC).date()
                - max(
                    price_dates[iid]
                    for iid in snapshot.result.get("input_version_ids", {}).get("prices", [])
                    if iid in price_dates
                )
            ).days
            for snapshot in snapshots
            if any(
                iid in price_dates
                for iid in snapshot.result.get("input_version_ids", {}).get("prices", [])
            )
        ]
        return {
            "window": "LATEST_1000_USER_PREDICTIONS",
            "prediction_count": len(predictions),
            "abstention_count": sum(
                p.result["confidence_status"] != "VALIDATED" for p in predictions
            ),
            "inference_failures": sum(
                p.result.get("reason") == "INFERENCE_FAILED" for p in predictions
            ),
            "models": statuses,
            "feature_missingness": {
                "status": "AVAILABLE",
                "missing_features": sum(q["missing_features"] for q in observed_quality),
                "observed_snapshots": len(observed_quality),
            }
            if observed_quality
            else {"status": "UNAVAILABLE", "reason": "NO_OBSERVED_FORECAST_INPUTS"},
            "data_freshness": {
                "status": "AVAILABLE",
                "observed_snapshots": len(ages),
                "oldest_latest_price_age_days": max(ages),
                "newest_latest_price_age_days": min(ages),
            }
            if ages
            else {"status": "UNAVAILABLE", "reason": "NO_OBSERVED_FORECAST_PRICE_INPUTS"},
            "llm_dependency": False,
            "automatic_production_promotion": False,
        }
