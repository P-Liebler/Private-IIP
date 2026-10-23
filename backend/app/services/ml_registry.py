import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.storage import get_storage
from app.ml.promotion import PROMOTION_RULES, promotion_reasons
from app.ml.registry_tracking import sync_status
from app.models import MLModelVersion, ModelPromotionReview, User
from app.schemas.pit import StrictModel
from app.services.fundamentals import digest
from app.services.ml_training import require_ml_operator
from app.services.pit_datasets import DatasetBuilder, code_manifest


class ModelReviewInput(StrictModel):
    status: Literal["EXPERIMENT", "VALIDATION", "SHADOW", "PRODUCTION", "RETIRED"]
    rationale: str = Field(min_length=20, max_length=4000)
    model_card: dict[str, str] = Field(default_factory=dict, max_length=20)


class ModelRegistryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def owned(self, model_id: UUID, user_id: UUID) -> MLModelVersion:
        model = await self.db.get(MLModelVersion, model_id)
        if model is None or model.user_id != user_id:
            raise AppError(404, "MODEL_NOT_FOUND", "Model not found")
        return model

    async def status(self, model_id: UUID) -> str:
        review = await self.db.scalar(
            select(ModelPromotionReview)
            .where(ModelPromotionReview.model_id == model_id)
            .order_by(ModelPromotionReview.created_at.desc(), ModelPromotionReview.id.desc())
            .limit(1)
        )
        return review.status if review else "EXPERIMENT"

    async def archived_bytes(self, model: MLModelVersion) -> tuple[bytes, dict[str, Any]]:
        """Read/hash/validate archive metadata; never load or execute a model."""
        expected_prefix = f"model-artifacts/{model.training_run_id}/"
        if not model.artifact_key.startswith(expected_prefix) or not model.artifact_key.endswith(
            f"{model.artifact_hash}.json"
        ):
            raise AppError(409, "ARTIFACT_URI_REJECTED", "Only internal model artifacts may load")
        data = await asyncio.to_thread(get_storage().get, model.artifact_key)
        if len(data) > 20_000_000 or hashlib.sha256(data).hexdigest() != model.artifact_hash:
            raise AppError(409, "ARTIFACT_HASH_MISMATCH", "Model artifact changed")
        artifact = json.loads(data)
        if (
            artifact.get("contract") != "internal-data-only-model-v1"
            or artifact.get("configuration") != model.configuration["request"]
            or artifact.get("training_code") != model.configuration["code"]
        ):
            raise AppError(409, "ARTIFACT_CONTRACT_MISMATCH", "Model artifact metadata changed")
        return data, dict(artifact)

    async def artifact(self, model: MLModelVersion) -> dict[str, Any]:
        _, artifact = await self.archived_bytes(model)
        if artifact["training_code"]["dependencies"] != code_manifest()["dependencies"]:
            raise AppError(409, "ARTIFACT_DEPENDENCY_MISMATCH", "Pinned dependencies differ")
        support = artifact["training_code"].get("supporting_dependencies")
        if support is not None and support != code_manifest()["supporting_dependencies"]:
            raise AppError(
                409, "ARTIFACT_DEPENDENCY_MISMATCH", "Pinned supporting dependencies differ"
            )
        return dict(artifact)

    async def review(
        self, model_id: UUID, body: ModelReviewInput, user: User
    ) -> ModelPromotionReview:
        require_ml_operator(user)
        model = await self.owned(model_id, user.id)
        # Serialize promotion/retirement so reviews never race on old state.
        await self.db.get(MLModelVersion, model.id, with_for_update=True)
        slot = int(
            digest({"user": str(user.id), "horizon": model.horizon, "target": model.target_type})[
                :15
            ],
            16,
        )
        if not await self.db.scalar(
            text("SELECT pg_try_advisory_xact_lock(:slot)"), {"slot": slot}
        ):
            raise AppError(
                409, "PROMOTION_CONCURRENT", "Another review for this forecast target is active"
            )
        await self.artifact(model)
        await DatasetBuilder(self.db).rebuild(model.dataset_id, user.id)
        if model.evaluation.get("promotion_rules") != PROMOTION_RULES:
            raise AppError(
                409, "PROMOTION_RULE_VERSION_MISMATCH", "Re-evaluate under current fixed rules"
            )
        evidence = dict(model.evaluation["promotion_evidence"])
        card_fields = {"purpose", "features", "periods", "validation", "calibration", "limitations"}
        evidence["model_card_verified"] = card_fields <= body.model_card.keys() and all(
            len(body.model_card[key]) >= 20 for key in card_fields
        )
        reasons = promotion_reasons(evidence)
        drift_review = await self.db.scalar(
            select(ModelPromotionReview)
            .where(
                ModelPromotionReview.model_id == model.id,
                ModelPromotionReview.evidence["origin"].astext == "MODEL_DEGRADED",
            )
            .limit(1)
        )
        if drift_review:
            reasons.append("DEGRADED_MODEL_REQUIRES_NEW_VALIDATION")
        champions = []
        if body.status == "PRODUCTION":
            candidates = (
                await self.db.scalars(
                    select(MLModelVersion)
                    .where(
                        MLModelVersion.user_id == user.id,
                        MLModelVersion.horizon == model.horizon,
                        MLModelVersion.target_type == model.target_type,
                        MLModelVersion.id != model.id,
                    )
                    .limit(100)
                )
            ).all()
            for current in candidates:
                if await self.status(current.id) != "PRODUCTION":
                    continue
                champions.append(current)
                request, current_request = (
                    model.configuration["request"],
                    current.configuration["request"],
                )
                if model.dataset_id != current.dataset_id or any(
                    request[k] != current_request[k]
                    for k in ("folds", "feature_names", "required_features")
                ):
                    reasons.append("CHAMPION_COMPARISON_REQUIRED")
                    continue
                loss = "brier" if model.target_type == "classification" else "rmse"
                if (
                    model.evaluation["aggregated_oos"][loss]
                    > current.evaluation["aggregated_oos"][loss]
                ):
                    reasons.append("CURRENT_CHAMPION_NOT_MATCHED")
        if body.status == "PRODUCTION" and reasons:
            raise AppError(422, "MODEL_PROMOTION_REJECTED", ", ".join(reasons))
        try:
            tracking_synced = await asyncio.to_thread(
                sync_status, str(model.id), model.mlflow_run_id, body.status
            )
        except Exception:
            tracking_synced = False
        if body.status == "PRODUCTION" and not tracking_synced:
            raise AppError(
                503, "MODEL_TRACKING_UNAVAILABLE", "Promotion requires verified tracking"
            )
        review = ModelPromotionReview(
            created_at=datetime.now(UTC),
            model_id=model.id,
            reviewer_id=user.id,
            status=body.status,
            evidence={
                "rationale": body.rationale,
                "rule_version": PROMOTION_RULES["version"],
                "gates": evidence,
                "reasons": reasons,
                "model_card": body.model_card,
                "model_card_hash": digest(body.model_card),
                "mlflow_synced": tracking_synced,
            },
        )
        self.db.add(review)
        for champion in champions:
            self.db.add(
                ModelPromotionReview(
                    model_id=champion.id,
                    reviewer_id=user.id,
                    status="RETIRED",
                    evidence={
                        "origin": "REPLACED_BY_REVIEWED_CHAMPION",
                        "replacement_id": str(model.id),
                    },
                )
            )
            try:
                await asyncio.to_thread(
                    sync_status, str(champion.id), champion.mlflow_run_id, "RETIRED"
                )
            except Exception:
                pass  # Application retirement remains authoritative.
        await self.db.commit()
        return review
