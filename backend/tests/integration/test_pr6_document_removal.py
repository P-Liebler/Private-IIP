"""Local synthetic document withdrawal preserves immutable originals and evidence."""

import asyncio
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.audit import intelligence_checkpoint
from app.assistant.documents import DocumentService
from app.assistant.runtime import TestOnlyProvider
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine
from app.models import ChunkEmbedding, DataSource, DocumentChunk, DocumentRemoval, ResearchDocument
from app.schemas.assistant import DocumentMetadata, DocumentRightsInput, RetrievalInput
from app.services.auth import AuthService
from app.services.raw_ingestion import RawIngestionService
from tests.unit.test_p10_contracts import pdf_bytes


@pytest.mark.integration
def test_withdrawal_is_owned_idempotent_append_only_and_never_reintroduced_at_old_cutoff(
    monkeypatch,
):
    class Storage:
        objects = {}

        def put(self, key, data, _content_type):
            self.objects[key] = data

        def get(self, key):
            return self.objects[key]

    storage = Storage()
    monkeypatch.setattr("app.services.raw_ingestion.get_storage", lambda: storage)

    async def run():
        try:
            async with get_engine().connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(
                        bind=connection,
                        join_transaction_mode="create_savepoint",
                        expire_on_commit=False,
                    ) as db:
                        user = await AuthService(db).create_user(
                            "pr6_doc_" + uuid4().hex[:10], "synthetic-document-password-6"
                        )
                        other = await AuthService(db).create_user(
                            "pr6_other_" + uuid4().hex[:10], "synthetic-document-password-6"
                        )
                        monkeypatch.setattr(
                            get_settings(), "data_operator_usernames", [user.username]
                        )
                        source = DataSource(
                            slug="TEST_PR6_DOC_" + uuid4().hex[:10].upper(),
                            name="SYNTHETIC PR6 self-authored PDF",
                            type="MANUAL",
                            trust_level="C",
                            enabled=True,
                            gate_status="APPROVED",
                            checked_at=datetime.now(UTC),
                            allowed_uses=["RAG_STORAGE", "RAG_INDEX", "RAG_METADATA"],
                        )
                        db.add(source)
                        await db.commit()
                        service = DocumentService(db, user.id, embeddings=TestOnlyProvider())
                        payload = pdf_bytes()
                        review = await service.review(
                            DocumentRightsInput(
                                source_slug=source.slug,
                                document_hash=hashlib.sha256(payload).hexdigest(),
                                storage_allowed=True,
                                indexing_allowed=True,
                                retention_policy="INDEFINITE_STORAGE_APPROVED",
                                attribution="Synthetic test author",
                                evidence=(
                                    "Self-authored synthetic fixture permits storage and "
                                    "indexing for isolated local testing."
                                ),
                            ),
                            user,
                        )
                        document = await service.import_pdf(
                            DocumentMetadata(
                                title="SYNTHETIC PR6 removable PDF",
                                source_slug=source.slug,
                                rights_review_id=review.id,
                            ),
                            payload,
                        )
                        did, raw_id = document.id, document.raw_ingestion_id
                        cutoff = datetime.now(UTC)
                        assert (await service.retrieve(RetrievalInput(query="synthetic")))[
                            "citations"
                        ]
                        before = await intelligence_checkpoint(db, user.id)
                        with pytest.raises(AppError) as foreign:
                            await DocumentService(db, other.id).remove(did)
                        assert foreign.value.status_code == 404
                        removal = await service.remove(did)
                        assert removal["status"] == "REMOVED_FROM_ACTIVE_LIBRARY"
                        assert (await service.remove(did))["removed_at"] == removal["removed_at"]
                        assert (
                            await db.scalar(
                                select(func.count())
                                .select_from(DocumentRemoval)
                                .where(DocumentRemoval.document_id == did)
                            )
                            == 1
                        )
                        with pytest.raises(AppError) as removed:
                            await service.original(did)
                        assert removed.value.code == "DOCUMENT_REMOVED"
                        assert not (await service.retrieve(RetrievalInput(query="synthetic")))[
                            "citations"
                        ]
                        assert not (
                            await service.retrieve(RetrievalInput(query="synthetic", as_of=cutoff))
                        )["citations"]
                        assert await RawIngestionService(db).get_verified(raw_id) == payload
                        assert await db.get(ResearchDocument, did) is not None
                        assert (
                            await db.scalar(
                                select(func.count())
                                .select_from(DocumentChunk)
                                .where(DocumentChunk.document_id == did)
                            )
                            > 0
                        )
                        assert (
                            await db.scalar(
                                select(func.count())
                                .select_from(ChunkEmbedding)
                                .join(DocumentChunk)
                                .where(DocumentChunk.document_id == did)
                            )
                            > 0
                        )
                        after = await intelligence_checkpoint(db, user.id)
                        assert (
                            after["intelligence_history_hash"]
                            == before["intelligence_history_hash"]
                        )
                        assert (
                            after["document_removal_history_hash"]
                            != before["document_removal_history_hash"]
                        )
                        for statement in (
                            update(DocumentRemoval)
                            .where(DocumentRemoval.document_id == did)
                            .values(reason="changed"),
                            delete(DocumentRemoval).where(DocumentRemoval.document_id == did),
                        ):
                            async with db.begin_nested() as savepoint:
                                with pytest.raises(DBAPIError):
                                    await db.execute(statement)
                                await savepoint.rollback()
                finally:
                    await outer.rollback()
        finally:
            await get_engine().dispose()

    asyncio.run(run())
