import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.metrics import observe
from app.assistant.runtime import EmbeddingProvider, provider
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    ChunkEmbedding,
    DataSource,
    DocumentChunk,
    DocumentRemoval,
    DocumentRightsReview,
    Instrument,
    ResearchDocument,
    User,
)
from app.schemas.assistant import DocumentMetadata, DocumentRightsInput, RetrievalInput
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

PIPELINE = "pypdf-6.21.2:plain-text-no-ocr:chunk600-overlap80-v3"


def require_data_operator(user: User) -> None:
    if user.username not in get_settings().data_operator_usernames:
        raise AppError(
            403,
            "DATA_OPERATOR_REQUIRED",
            "An explicitly authorized data operator must review this evidence",
        )


def cutoff_time(value: datetime | None) -> datetime:
    now = datetime.now(UTC)
    if value is not None and value > now:
        raise AppError(
            422, "FUTURE_CUTOFF_REJECTED", "Only already available information can be queried"
        )
    return value.astimezone(UTC) if value is not None else now


async def parse_pdf(data: bytes) -> list[dict[str, Any]]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.assistant.pdf_worker",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(15):
            output, _ = await process.communicate(data)
        if len(output) > 800_000 or process.returncode != 0:
            raise ValueError("PDF resource limit")
        result = json.loads(output)
        if not result.get("pages"):
            raise ValueError("PDF extraction failed")
        return list(result["pages"])
    except (ValueError, TimeoutError) as error:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise AppError(
            422, "PDF_EXTRACTION_UNAVAILABLE", "Das PDF enthält keinen sicher extrahierbaren Text"
        ) from error
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise


def chunks(pages: list[dict[str, Any]]) -> list[tuple[int, str]]:
    result = []
    for page in pages:
        text = str(page["text"]).replace("\x00", "").strip()
        for start in range(0, len(text), 520):
            content = text[start : start + 600].strip()
            if content:
                result.append((int(page["page"]), content))
    if len(result) > 200:
        raise AppError(422, "DOCUMENT_CHUNK_LIMIT", "Document exceeds the chunk limit")
    return result


class DocumentService:
    def __init__(
        self,
        db: AsyncSession,
        user_id: UUID,
        raw: RawIngestionService | None = None,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self.db, self.user_id = db, user_id
        self.raw = raw or RawIngestionService(db)
        self.embeddings = embeddings or provider()

    async def owned(self, identifier: UUID) -> ResearchDocument:
        document = await self.db.get(ResearchDocument, identifier)
        if document is None or document.user_id != self.user_id:
            raise AppError(404, "DOCUMENT_NOT_FOUND", "Document not found")
        if await self.db.scalar(
            select(DocumentRemoval.id).where(DocumentRemoval.document_id == identifier)
        ):
            raise AppError(410, "DOCUMENT_REMOVED", "Document was removed from the active library")
        return document

    async def remove(self, identifier: UUID) -> dict[str, Any]:
        document = await self.db.get(ResearchDocument, identifier, with_for_update=True)
        if document is None or document.user_id != self.user_id:
            raise AppError(404, "DOCUMENT_NOT_FOUND", "Document not found")
        removal = await self.db.scalar(
            select(DocumentRemoval).where(DocumentRemoval.document_id == identifier)
        )
        if removal is None:
            removal = DocumentRemoval(
                user_id=self.user_id,
                document_id=identifier,
                reason="OWNER_WITHDRAWAL_FROM_ACTIVE_LIBRARY",
            )
            self.db.add(removal)
            await self.db.commit()
        return {
            "id": identifier,
            "status": "REMOVED_FROM_ACTIVE_LIBRARY",
            "removed_at": removal.created_at,
            "raw_retention": "IMMUTABLE_AUDIT_ORIGINAL_RETAINED",
        }

    async def review(self, request: DocumentRightsInput, user: User) -> DocumentRightsReview:
        require_data_operator(user)
        source = await SourceService(self.db).get(request.source_slug)
        SourceGate.require_enabled(
            source, "RAG_STORAGE" if request.storage_allowed else "RAG_METADATA"
        )
        if request.indexing_allowed:
            SourceGate.require_enabled(source, "RAG_INDEX")
        if request.indexing_allowed and (
            not request.storage_allowed or request.retention_policy != "INDEFINITE_STORAGE_APPROVED"
        ):
            raise AppError(
                422,
                "DOCUMENT_RIGHTS_INCOMPATIBLE",
                "Indexing requires an approved durable original",
            )
        row = DocumentRightsReview(
            user_id=self.user_id,
            source_id=source.id,
            document_hash=request.document_hash,
            rights=request.model_dump(mode="json"),
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def import_pdf(self, request: DocumentMetadata, data: bytes) -> ResearchDocument:
        source = await SourceService(self.db).get(request.source_slug)
        SourceGate.require_enabled(source, "RAG_STORAGE")
        review = (
            await self.db.get(DocumentRightsReview, request.rights_review_id)
            if request.rights_review_id
            else None
        )
        if not review or review.user_id != self.user_id or review.source_id != source.id:
            raise AppError(
                403,
                "DOCUMENT_RIGHTS_REVIEW_REQUIRED",
                "Eine dokumentbezogene Rechtefreigabe ist erforderlich",
            )
        rights = review.rights
        if (
            not rights["storage_allowed"]
            or rights["retention_policy"] != "INDEFINITE_STORAGE_APPROVED"
        ):
            raise AppError(
                403, "DOCUMENT_STORAGE_NOT_APPROVED", "Full-text storage is not approved"
            )
        content_hash = hashlib.sha256(data).hexdigest()
        if content_hash != review.document_hash:
            raise AppError(
                409,
                "DOCUMENT_RIGHTS_HASH_MISMATCH",
                "Rights review refers to different document bytes",
            )
        if request.instrument_id and await self.db.get(Instrument, request.instrument_id) is None:
            raise AppError(422, "INSTRUMENT_NOT_FOUND", "Document instrument is unknown")
        if get_settings().assistant_test_mode and not source.slug.startswith("TEST_"):
            raise AppError(
                403, "TEST_SOURCE_REQUIRED", "Test embeddings cannot index real source documents"
            )
        # Original exact bytes are durable and verified before validation or parsing.
        raw = await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="RAG_DOCUMENT_PDF",
            instrument_id=request.instrument_id,
            content_type="application/pdf",
            request_metadata={"user_id": str(self.user_id), "filename": content_hash + ".pdf"},
        )
        verified = await self.raw.get_verified(raw.id)
        status, metadata, extracted, vectors = (
            "RAW_ONLY",
            {
                "pipeline_version": PIPELINE,
                "source_checked_at": source.checked_at.isoformat() if source.checked_at else None,
            },
            [],
            [],
        )
        model_version = None
        if rights["indexing_allowed"]:
            SourceGate.require_enabled(source, "RAG_INDEX")
            try:
                extracted = chunks(await parse_pdf(verified))
                status = "TEXT_EXTRACTED"
                try:
                    async with asyncio.timeout(60):
                        for start in range(0, len(extracted), 8):
                            batch, version = await self.embeddings.embed(
                                [text for _, text in extracted[start : start + 8]]
                            )
                            if model_version is not None and version != model_version:
                                raise AppError(
                                    503,
                                    "EMBEDDING_MODEL_CHANGED",
                                    "Embedding version changed during import",
                                )
                            model_version = version
                            vectors.extend(batch)
                    status = "INDEXED"
                except (AppError, TimeoutError) as error:
                    vectors = []
                    metadata["embedding_error"] = (
                        error.code if isinstance(error, AppError) else "EMBEDDING_TIMEOUT"
                    )
                    status = "EMBEDDING_UNAVAILABLE"
            except AppError as error:
                metadata["extraction_error"] = error.code
                status = "EXTRACTION_UNAVAILABLE"
        now = datetime.now(UTC)
        document = ResearchDocument(
            user_id=self.user_id,
            instrument_id=request.instrument_id,
            source_id=source.id,
            rights_review_id=review.id,
            raw_ingestion_id=raw.id,
            title=request.title,
            document_type=request.document_type,
            published_at=request.published_at,
            known_at=request.published_at or raw.received_at,
            observed_at=raw.received_at,
            content_hash=content_hash,
            object_key=raw.object_path,
            processing_status=status,
            processing_metadata={
                **metadata,
                "embedding_model_version": model_version,
                "publication_time_provenance": "USER_RECORDED_OR_FIRST_LOCAL_OBSERVATION",
            },
            created_at=now,
        )
        self.db.add(document)
        await self.db.flush()
        for index, (page, content) in enumerate(extracted):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                page_number=page,
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                created_at=now,
            )
            self.db.add(chunk)
            await self.db.flush()
            if vectors and model_version:
                self.db.add(
                    ChunkEmbedding(
                        chunk_id=chunk.id,
                        model_version=model_version,
                        embedding=vectors[index],
                        created_at=now,
                    )
                )
        await self.db.commit()
        return document

    async def original(self, identifier: UUID) -> bytes:
        document = await self.owned(identifier)
        source = await self.db.get(DataSource, document.source_id)
        assert source
        SourceGate.require_enabled(source, "RAG_STORAGE")
        if not document.raw_ingestion_id:
            raise AppError(409, "DOCUMENT_ORIGINAL_UNAVAILABLE", "Only metadata is archived")
        return await self.raw.get_verified(document.raw_ingestion_id)

    async def metadata_only(self, request: DocumentMetadata) -> ResearchDocument:
        source = await SourceService(self.db).get(request.source_slug)
        SourceGate.require_enabled(source, "RAG_METADATA")
        if request.instrument_id and await self.db.get(Instrument, request.instrument_id) is None:
            raise AppError(422, "INSTRUMENT_NOT_FOUND", "Document instrument is unknown")
        now = datetime.now(UTC)
        document = ResearchDocument(
            user_id=self.user_id,
            source_id=source.id,
            instrument_id=request.instrument_id,
            title=request.title,
            document_type=request.document_type,
            published_at=request.published_at,
            known_at=request.published_at or now,
            observed_at=now,
            processing_status="METADATA_ONLY",
            processing_metadata={
                "content_storage": "NOT_APPROVED_OR_NOT_REQUESTED",
                "publication_time_provenance": "USER_RECORDED",
            },
            created_at=now,
        )
        self.db.add(document)
        await self.db.commit()
        return document

    async def reindex(self, identifier: UUID) -> dict[str, Any]:
        document = await self.owned(identifier)
        review = (
            await self.db.get(DocumentRightsReview, document.rights_review_id)
            if document.rights_review_id
            else None
        )
        source = await self.db.get(DataSource, document.source_id)
        if not source or not review or not review.rights["indexing_allowed"]:
            raise AppError(403, "DOCUMENT_INDEXING_NOT_APPROVED", "Indexing is not approved")
        SourceGate.require_enabled(source, "RAG_INDEX")
        if get_settings().assistant_test_mode and not source.slug.startswith("TEST_"):
            raise AppError(
                403, "TEST_SOURCE_REQUIRED", "Test embeddings cannot index real documents"
            )
        await self.original(identifier)
        stored = (
            await self.db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.chunk_index)
            )
        ).all()
        if not stored:
            return {"status": "EXTRACTION_UNAVAILABLE", "new_embeddings": 0}
        added = 0
        for start in range(0, len(stored), 8):
            batch = stored[start : start + 8]
            if any(hashlib.sha256(c.content.encode()).hexdigest() != c.content_hash for c in batch):
                raise AppError(409, "CHUNK_INTEGRITY_ERROR", "Stored chunk integrity mismatch")
            vectors, version = await self.embeddings.embed([c.content for c in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                previous = await self.db.scalar(
                    select(ChunkEmbedding).where(
                        ChunkEmbedding.chunk_id == chunk.id, ChunkEmbedding.model_version == version
                    )
                )
                if not previous:
                    self.db.add(
                        ChunkEmbedding(
                            chunk_id=chunk.id,
                            model_version=version,
                            embedding=vector,
                            created_at=datetime.now(UTC),
                        )
                    )
                    added += 1
        await self.db.commit()
        return {"status": "INDEXED", "new_embeddings": added}

    async def retrieve(self, request: RetrievalInput) -> dict[str, Any]:
        cutoff = cutoff_time(request.as_of)
        statement = select(ResearchDocument).where(
            ResearchDocument.user_id == self.user_id,
            ResearchDocument.known_at <= cutoff,
            ResearchDocument.observed_at <= cutoff,
            ResearchDocument.created_at <= cutoff,
            ~select(DocumentRemoval.id)
            .where(DocumentRemoval.document_id == ResearchDocument.id)
            .exists(),
        )
        if request.instrument_id:
            statement = statement.where(ResearchDocument.instrument_id == request.instrument_id)
        if request.document_type:
            statement = statement.where(ResearchDocument.document_type == request.document_type)
        if request.source_id:
            statement = statement.where(ResearchDocument.source_id == request.source_id)
        if request.published_from:
            statement = statement.where(ResearchDocument.published_at >= request.published_from)
        if request.published_to:
            statement = statement.where(ResearchDocument.published_at <= request.published_to)
        documents = (
            await self.db.scalars(
                statement.order_by(ResearchDocument.created_at.desc()).limit(1000)
            )
        ).all()
        eligible = {}
        for document in documents:
            review = (
                await self.db.get(DocumentRightsReview, document.rights_review_id)
                if document.rights_review_id
                else None
            )
            source = (
                await SourceService(self.db).get(review.rights["source_slug"]) if review else None
            )
            try:
                if source is None or not review or not review.rights["indexing_allowed"]:
                    continue
                SourceGate.require_enabled(source, "RAG_INDEX")
                SourceGate.require_enabled(source, "RAG_STORAGE")
                eligible[document.id] = (document, source, review)
            except AppError:
                continue
        if not eligible:
            observe("retrieval", False)
            return {
                "status": "RETRIEVAL_UNAVAILABLE",
                "reason": "NO_PERMITTED_DOCUMENTS_AT_CUTOFF",
                "citations": [],
            }
        try:
            query_vectors, version = await self.embeddings.embed([request.query])
        except AppError as error:
            observe("retrieval", False)
            return {"status": "RETRIEVAL_UNAVAILABLE", "reason": error.code, "citations": []}
        rows = (
            await self.db.execute(
                select(DocumentChunk, ChunkEmbedding)
                .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .where(
                    DocumentChunk.document_id.in_(eligible),
                    DocumentChunk.created_at <= cutoff,
                    ChunkEmbedding.created_at <= cutoff,
                    ChunkEmbedding.model_version == version,
                )
                .order_by(
                    ChunkEmbedding.embedding.cosine_distance(query_vectors[0]), DocumentChunk.id
                )
                .limit(request.limit)
            )
        ).all()
        citations = []
        verified_documents = set()
        for chunk, embedding in rows:
            document, source, review = eligible[chunk.document_id]
            if document.id not in verified_documents:
                try:
                    if not document.raw_ingestion_id:
                        continue
                    await self.raw.get_verified(document.raw_ingestion_id)
                except AppError:
                    continue
                verified_documents.add(document.id)
            if hashlib.sha256(chunk.content.encode()).hexdigest() != chunk.content_hash:
                continue
            citations.append(
                {
                    "document_id": str(document.id),
                    "source": source.name,
                    "title": document.title,
                    "published_at": document.published_at.isoformat()
                    if document.published_at
                    else None,
                    "known_at": document.known_at.isoformat(),
                    "observed_at": document.observed_at.isoformat(),
                    "chunk_id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                    "content_hash": chunk.content_hash,
                    "document_hash": document.content_hash,
                    "embedding_model_version": embedding.model_version,
                    "attribution": review.rights["attribution"],
                    "url": f"/api/v1/research-documents/{document.id}/original",
                    "verification_scope": "EXACT_ARCHIVED_TEXT_NOT_VALIDATED_FINANCIAL_VALUES",
                }
            )
        observe("retrieval", bool(citations))
        return {
            "status": "AVAILABLE" if citations else "RETRIEVAL_UNAVAILABLE",
            "reason": None if citations else "NO_MATCHING_ARCHIVED_EMBEDDING_VERSION",
            "citations": citations,
            "embedding_model_version": version,
            "availability_cutoff": cutoff.isoformat(),
        }
