from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.readiness import audit_readiness
from app.models import FeatureSnapshot
from app.services.pit_datasets import DatasetBuilder


class P7DataReadinessService:
    def __init__(self, db: AsyncSession) -> None:
        self.datasets = DatasetBuilder(db)

    async def report(
        self, dataset_id: UUID, user_id: UUID, required_features: list[str], horizon: int
    ) -> dict[str, Any]:
        dataset = await self.datasets.owned(dataset_id, user_id)
        if dataset.configuration["target_horizon"] != horizon:
            raise AppError(422, "TARGET_HORIZON_MISMATCH", "Dataset horizon differs")
        # Evidence includes canonical hashes and original bytes, not a UI claim.
        replay = await self.datasets.rebuild(dataset_id, user_id)
        feature_ids = {
            UUID(r["feature_snapshot_id"]) for r in dataset.rows if r.get("feature_snapshot_id")
        }
        snapshots = {
            str(r.id): r
            for r in (
                await self.datasets.db.scalars(
                    select(FeatureSnapshot).where(FeatureSnapshot.id.in_(feature_ids))
                )
            ).all()
        }
        violations = []
        for index, row in enumerate(dataset.rows):
            if not row.get("eligible"):
                continue
            snapshot = snapshots.get(str(row.get("feature_snapshot_id", "")))
            cutoff = datetime.fromisoformat(row["information_cutoff_at"])
            if (
                snapshot is None
                or str(snapshot.instrument_id) != row["instrument_id"]
                or snapshot.information_cutoff_at > cutoff
                or snapshot.as_of > cutoff
                or snapshot.result["features"] != row["features"]
            ):
                violations.append(str(index))
        result = audit_readiness(
            dataset.configuration,
            dataset.rows,
            dataset.quality,
            required_features,
            horizon,
            datetime.now(UTC),
        )
        if violations:
            result.update(
                {
                    "status": "DATA_QUALITY_FAILED",
                    "production_data_eligible": False,
                    "feature_contract_violations": violations,
                    "eligible_row_ids": [],
                    "eligible_observations": 0,
                }
            )
        return {**result, "dataset_id": str(dataset_id), "pinned_replay": replay}
