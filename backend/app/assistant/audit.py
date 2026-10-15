import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.research import view
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AlertRule,
    AlertRuleVersion,
    AssistantConversation,
    AssistantMessage,
    AssistantToolCall,
    ChunkEmbedding,
    DailyBrief,
    DailyBriefConfig,
    DocumentChunk,
    DocumentRightsReview,
    FinancialEventVersion,
    Notification,
    OptimizerRun,
    ResearchDocument,
)
from app.services.fundamentals import digest
from app.services.raw_ingestion import RawIngestionService


async def intelligence_checkpoint(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    content: dict[str, Any] = {}
    model: Any
    for model in (
        AssistantConversation,
        AssistantMessage,
        AssistantToolCall,
        DocumentRightsReview,
        ResearchDocument,
        FinancialEventVersion,
        AlertRule,
        AlertRuleVersion,
        AlertEvaluation,
        AlertEvent,
        Notification,
        DailyBriefConfig,
        DailyBrief,
        OptimizerRun,
    ):
        ordering = model.user_id if model is DailyBriefConfig else model.id
        rows = (
            await db.scalars(select(model).where(model.user_id == user_id).order_by(ordering))
        ).all()
        content[model.__tablename__] = [view(r) for r in rows]
    documents = (
        await db.scalars(
            select(ResearchDocument)
            .where(ResearchDocument.user_id == user_id)
            .order_by(ResearchDocument.id)
        )
    ).all()
    raw = RawIngestionService(db)
    for document in documents:
        if document.raw_ingestion_id:
            original = await raw.get_verified(document.raw_ingestion_id)
            assert hashlib.sha256(original).hexdigest() == document.content_hash
    chunks = (
        await db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_([r.id for r in documents]))
            .order_by(DocumentChunk.id)
        )
    ).all()
    for chunk in chunks:
        assert hashlib.sha256(chunk.content.encode()).hexdigest() == chunk.content_hash
    content["chunks"] = [view(c) for c in chunks]
    embeddings = (
        await db.scalars(
            select(ChunkEmbedding)
            .where(ChunkEmbedding.chunk_id.in_([c.id for c in chunks]))
            .order_by(ChunkEmbedding.id)
        )
    ).all()
    content["embeddings"] = [
        {
            "id": str(e.id),
            "chunk_id": str(e.chunk_id),
            "model_version": e.model_version,
            "created_at": e.created_at.isoformat(),
            "embedding": [float(v) for v in e.embedding],
        }
        for e in embeddings
    ]
    for event in content["financial_event_versions"]:
        await raw.get_verified(UUID(str(event["raw_ingestion_id"])))
    return {
        "intelligence_history_hash": digest(content),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedding_count": len(embeddings),
        "message_count": len(content["assistant_messages"]),
        "alert_evaluation_count": len(content["alert_evaluations"]),
        "brief_count": len(content["daily_briefs"]),
        "optimizer_count": len(content["optimizer_runs"]),
        "calendar_version_count": len(content["financial_event_versions"]),
        "alert_event_count": len(content["alert_events"]),
        "notification_count": len(content["notifications"]),
    }
