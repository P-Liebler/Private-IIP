"""Actual local embedding/RAG and original-byte contract in synthetic staging."""
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
import sys
from uuid import UUID

from sqlalchemy import select

from app.assistant.documents import DocumentService
from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import User
from app.schemas.assistant import RetrievalInput


async def main(control):
    settings = get_settings()
    assert settings.app_env == "staging" and not settings.assistant_test_mode
    assert settings.minio_endpoint == "caddy:9002" and settings.minio_secure
    assert control["username"].startswith("restore_")
    try:
        async with get_session_factory()() as db:
            user = await db.scalar(select(User).where(User.username == control["username"]))
            assert user
            service = DocumentService(db, user.id)
            document = await service.owned(UUID(control["document_id"]))
            original = await service.original(document.id)
            assert hashlib.sha256(original).hexdigest() == document.content_hash
            result = await service.retrieve(RetrievalInput(query="synthetic document provenance", limit=4))
            assert result["status"] == "AVAILABLE" and any(c["document_id"] == str(document.id) for c in result["citations"])
            assert result["embedding_model_version"].startswith("ollama/0.40.11:")
            assert all(c["verification_scope"] == "EXACT_ARCHIVED_TEXT_NOT_VALIDATED_FINANCIAL_VALUES" for c in result["citations"])
            past = await service.retrieve(RetrievalInput(query="synthetic document provenance",
                as_of=datetime.now(UTC) - timedelta(days=1), limit=4))
            assert past["status"] == "RETRIEVAL_UNAVAILABLE" and not past["citations"]
            print(json.dumps({"status": "NATIVE_LOCAL_RAG_VERIFIED", "original_sha256": document.content_hash,
                "embedding_model_version": result["embedding_model_version"], "citations": len(result["citations"]),
                "historical_local_availability_gate": True, "synthetic_only": True}))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main(json.loads(sys.stdin.readline())))
