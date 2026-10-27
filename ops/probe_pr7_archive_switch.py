"""Read actual archived originals through one explicitly configured staging factory."""
import asyncio
import hashlib
import json
import sys
from uuid import UUID

from sqlalchemy import select

from app.assistant.documents import DocumentService
from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import DocumentRemoval, ResearchDocument, User
from app.services.ml_registry import ModelRegistryService
from app.services.raw_ingestion import RawIngestionService


async def main(control):
    settings = get_settings()
    assert settings.minio_secure and not settings.assistant_test_mode
    assert settings.minio_endpoint in {"caddy:9002", "caddy:9003"}
    # The read-only original is the existing local development source. Its
    # development credentials never become the staging server configuration.
    assert settings.app_env == ("staging" if control["phase"] == "target" else "local")
    assert control["username"].startswith("restore_")
    try:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == control["username"]))
            assert user
            raw = await RawIngestionService(db).get_verified(UUID(control["raw_id"]))
            registry = ModelRegistryService(db)
            model = await registry.owned(UUID(control["model_id"]), user.id)
            data, _ = await registry.archived_bytes(model)
            assert hashlib.sha256(data).hexdigest() == control["model_artifact_hash"]
            document = await db.scalar(select(ResearchDocument).where(
                ResearchDocument.user_id == user.id, ResearchDocument.object_key.is_not(None),
                ~select(DocumentRemoval.id).where(DocumentRemoval.document_id == ResearchDocument.id).exists()
            ).order_by(ResearchDocument.id).limit(1))
            document_hash = None
            if document:
                original = await DocumentService(db, user.id).original(document.id)
                document_hash = hashlib.sha256(original).hexdigest()
                assert document_hash == document.content_hash
            print(json.dumps({"status": "ARCHIVE_FACTORY_READ_VERIFIED", "phase": control["phase"],
                "raw_sha256": hashlib.sha256(raw).hexdigest(), "model_sha256": model.artifact_hash,
                "document_sha256": document_hash, "model_execution": False,
                "application_endpoint_changed": False}))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main(json.loads(sys.stdin.readline())))
