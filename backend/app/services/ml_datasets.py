import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.datasets import compose_windows
from app.models import DatasetVersion
from app.services.pit_datasets import DatasetBuilder


class MLDatasetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def compose(self, ids: list[UUID], user_id: UUID) -> DatasetVersion:
        if not 2 <= len(ids) <= 8 or len(set(ids)) != len(ids):
            raise AppError(422, "COMPOSITION_WINDOW_LIMIT", "Select 2–8 distinct pinned windows")
        if not await self.db.scalar(text("SELECT pg_try_advisory_xact_lock(608613)")):
            raise AppError(409, "BUILD_LIMIT", "A dataset build is already active")
        async with asyncio.timeout(240):
            builder = DatasetBuilder(self.db)
            windows: list[dict[str, Any]] = []
            for iid in ids:
                row = await builder.owned(iid, user_id)
                if row.configuration.get("composition_version"):
                    raise AppError(422, "NESTED_COMPOSITION_FORBIDDEN", "Use original P6 windows")
                await builder.rebuild(iid, user_id)
                windows.append(
                    {
                        "id": str(row.id),
                        "content_hash": row.content_hash,
                        "configuration": row.configuration,
                        "manifest": row.manifest,
                        "rows": row.rows,
                        "quality": row.quality,
                    }
                )
            try:
                content = compose_windows(windows)
            except ValueError as error:
                raise AppError(422, str(error), "Dataset windows are incompatible") from error
            existing = await self.db.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.user_id == user_id,
                    DatasetVersion.content_hash == content["content_hash"],
                )
            )
            if existing:
                return existing
            dataset = DatasetVersion(
                user_id=user_id,
                universe_id=UUID(content["configuration"]["universe_id"]),
                **content,
            )
            self.db.add(dataset)
            await self.db.flush()
            return dataset
