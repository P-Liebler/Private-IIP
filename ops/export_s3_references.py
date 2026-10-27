"""Pipe into the API container; read-only private S3 reference export.

Quiesce writers and retain this output with the DB dump and migration manifest.
Includes withdrawn documents. Removal/UI histories remain in the DB dump and
their separate archive checkpoints; they are not new object references.
"""
import asyncio
import json

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import MLModelVersion, RawIngestion, ResearchDocument


async def main():
    try:
        async with get_session_factory()() as db:
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            bucket = get_settings().minio_bucket_raw
            rows = []
            for model, key_column, hash_column, condition in (
                (RawIngestion, RawIngestion.object_path, RawIngestion.sha256, RawIngestion.status == "STORED"),
                (MLModelVersion, MLModelVersion.artifact_key, MLModelVersion.artifact_hash, MLModelVersion.artifact_key.is_not(None)),
                (ResearchDocument, ResearchDocument.object_key, ResearchDocument.content_hash, ResearchDocument.object_key.is_not(None)),
            ):
                for row_id, key, checksum in (await db.execute(
                    select(model.id, key_column, hash_column).where(condition).order_by(model.id)
                )).all():
                    if not key or not checksum:
                        raise RuntimeError("INCOMPLETE_OBJECT_REFERENCE")
                    rows.append({"table": model.__tablename__, "id": str(row_id),
                                 "bucket": bucket, "key": key, "sha256": checksum})
            print(json.dumps(rows, sort_keys=True))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
