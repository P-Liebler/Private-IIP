import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.assistant.documents import DocumentService, cutoff_time
from app.assistant.orchestration import AssistantService
from app.assistant.runtime import OllamaProvider, TestOnlyProvider
from app.assistant.tools import ToolRegistry
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.db.session import get_session
from app.models import (
    AssistantConversation,
    AssistantMessage,
    AssistantToolCall,
    ChunkEmbedding,
    DocumentChunk,
    DocumentRightsReview,
    ResearchDocument,
)
from app.schemas.assistant import (
    ChatInput,
    ConversationCreate,
    DocumentMetadata,
    DocumentRightsInput,
    RetrievalInput,
    ToolInput,
)
from app.services.auth import AuthContext
from app.services.portfolios import PortfolioService
from app.services.rate_limit import rate_limiter
from app.services.work_limits import work_slot

router = APIRouter(prefix="/api/v1", tags=["local-assistant"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.get("/assistant/status")
async def status(context: Auth) -> dict[str, Any]:
    settings = get_settings()
    if settings.assistant_test_mode:
        return {
            "status": "TEST_ONLY_STUB",
            "model_version": TestOnlyProvider.version_name,
            "local_only": True,
        }
    runtime = OllamaProvider()
    try:
        async with asyncio.timeout(4):
            versions = [
                await runtime.version(settings.ollama_chat_model),
                await runtime.version(settings.ollama_embedding_model),
            ]
        return {"status": "AVAILABLE", "model_versions": versions, "local_only": True}
    except (AppError, TimeoutError):
        return {
            "status": "LLM_UNAVAILABLE",
            "local_only": True,
            "configured_models": [settings.ollama_chat_model, settings.ollama_embedding_model],
        }


@router.post("/assistant/conversations", status_code=201)
async def create_conversation(request: ConversationCreate, db: DB, context: Auth) -> dict[str, Any]:
    return view(await AssistantService(db, context.user.id).create(request))


@router.get("/assistant/conversations")
async def conversations(
    db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == context.user.id)
            .order_by(AssistantConversation.created_at.desc(), AssistantConversation.id.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.delete("/assistant/conversations/{identifier}", status_code=204)
async def remove_conversation(identifier: UUID, db: DB, context: Auth) -> Response:
    await AssistantService(db, context.user.id).remove(identifier)
    return Response(status_code=204)


@router.get("/assistant/conversations/{identifier}/messages")
async def messages(
    identifier: UUID, db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    await AssistantService(db, context.user.id).owned(identifier)
    rows = (
        await db.scalars(
            select(AssistantMessage)
            .where(
                AssistantMessage.conversation_id == identifier,
                AssistantMessage.user_id == context.user.id,
            )
            .order_by(AssistantMessage.created_at, AssistantMessage.id)
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.post("/assistant/conversations/{identifier}/messages")
async def ask(identifier: UUID, request: ChatInput, db: DB, context: Auth) -> StreamingResponse:
    service = AssistantService(db, context.user.id)
    await service.owned(identifier)
    if request.portfolio_id:
        await PortfolioService(db, context.user.id).owned(request.portfolio_id)
    if get_settings().assistant_test_mode and not context.user.username.startswith(
        ("restore_", "p10_", "test_")
    ):
        raise AppError(
            403, "TEST_USER_REQUIRED", "Test provider is restricted to explicit fixture users"
        )

    cutoff_time(request.as_of)
    await rate_limiter.check_work("assistant", str(context.user.id), maximum=6)

    async def events() -> AsyncIterator[str]:
        async for event in service.stream(identifier, request):
            yield "data: " + json.dumps(event, ensure_ascii=False, default=str) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/assistant/tools/invoke")
async def invoke(request: ToolInput, db: DB, context: Auth) -> list[dict[str, Any]]:
    await rate_limiter.check_work("assistant-tools", str(context.user.id), maximum=30)
    return [
        fact.model_dump(mode="json")
        for fact in await ToolRegistry(db, context.user.id).call(request)
    ]


@router.get("/assistant/tool-calls/{identifier}")
async def tool_call(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    row = await db.get(AssistantToolCall, identifier)
    if not row or row.user_id != context.user.id:
        raise AppError(404, "TOOL_CALL_NOT_FOUND", "Tool call not found")
    return view(row)


@router.post("/research-documents/rights-reviews", status_code=201)
async def rights_review(request: DocumentRightsInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await DocumentService(db, context.user.id).review(request, context.user))


@router.get("/research-documents/rights-reviews")
async def rights_history(db: DB, context: Auth) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(DocumentRightsReview)
            .where(DocumentRightsReview.user_id == context.user.id)
            .order_by(DocumentRightsReview.created_at.desc())
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.post("/research-documents/uploads", status_code=201)
async def prepare_upload(request: DocumentMetadata, db: DB, context: Auth) -> dict[str, Any]:
    # Transport metadata is separate from the original PDF bytes and never logged in URLs.
    from app.services.sources import SourceGate, SourceService

    source = await SourceService(db).get(request.source_slug)
    SourceGate.require_enabled(source, "RAG_STORAGE")
    review = (
        await db.get(DocumentRightsReview, request.rights_review_id)
        if request.rights_review_id
        else None
    )
    if (
        not review
        or review.user_id != context.user.id
        or review.source_id != source.id
        or not review.rights["storage_allowed"]
    ):
        raise AppError(403, "DOCUMENT_RIGHTS_REVIEW_REQUIRED", "Document rights review is required")
    identifier = uuid4()
    client = make_valkey_client()
    try:
        await client.setex(
            f"document-upload:{context.user.id}:{identifier}", 900, request.model_dump_json()
        )
    except RedisError as error:
        raise AppError(
            503, "UPLOAD_UNAVAILABLE", "Upload preparation is temporarily unavailable"
        ) from error
    finally:
        await client.aclose()
    return {"upload_id": identifier, "expires_in_seconds": 900, "maximum_bytes": 5000000}


@router.post("/research-documents/uploads/{identifier}/content", status_code=201)
async def upload(identifier: UUID, request: Request, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("document-upload", str(context.user.id), maximum=4)
    client = make_valkey_client()
    try:
        raw_metadata = await client.getdel(f"document-upload:{context.user.id}:{identifier}")
    except RedisError as error:
        raise AppError(
            503, "UPLOAD_UNAVAILABLE", "Upload preparation is temporarily unavailable"
        ) from error
    finally:
        await client.aclose()
    if not raw_metadata:
        raise AppError(
            404, "UPLOAD_NOT_FOUND", "Upload is unknown, expired or belongs to another user"
        )
    metadata = DocumentMetadata.model_validate_json(raw_metadata)
    body = bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body) > 5_000_000:
            raise AppError(413, "DOCUMENT_SIZE_LIMIT", "Document exceeds 5 MB")
    async with work_slot(608711):
        return view(await DocumentService(db, context.user.id).import_pdf(metadata, bytes(body)))


@router.post("/research-documents/metadata", status_code=201)
async def metadata_only(request: DocumentMetadata, db: DB, context: Auth) -> dict[str, Any]:
    return view(await DocumentService(db, context.user.id).metadata_only(request))


@router.post("/research-documents/retrieve")
async def retrieve(request: RetrievalInput, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("retrieval", str(context.user.id), maximum=20)
    return await DocumentService(db, context.user.id).retrieve(request)


@router.get("/research-documents")
async def documents(
    db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(ResearchDocument)
            .where(ResearchDocument.user_id == context.user.id)
            .order_by(ResearchDocument.created_at.desc(), ResearchDocument.id.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.get("/research-documents/{identifier}")
async def document_detail(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    row = await DocumentService(db, context.user.id).owned(identifier)
    counts = (
        await db.execute(
            select(ChunkEmbedding.model_version, func.count())
            .join(DocumentChunk, DocumentChunk.id == ChunkEmbedding.chunk_id)
            .where(DocumentChunk.document_id == identifier)
            .group_by(ChunkEmbedding.model_version)
        )
    ).all()
    return {**view(row), "embedding_versions": {version: count for version, count in counts}}


@router.get("/research-documents/{identifier}/original")
async def original(identifier: UUID, db: DB, context: Auth) -> Response:
    data = await DocumentService(db, context.user.id).original(identifier)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{identifier}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/research-documents/{identifier}/reindex")
async def reindex(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("document-reindex", str(context.user.id), maximum=4)
    async with work_slot(608711), asyncio.timeout(120):
        return await DocumentService(db, context.user.id).reindex(identifier)
