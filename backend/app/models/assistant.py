from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OwnedRecord:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AssistantConversation(OwnedRecord, Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_conversation_user_created", "user_id", "created_at"),)
    title: Mapped[str] = mapped_column(String(120), nullable=False)


class AssistantMessage(OwnedRecord, Base):
    __tablename__ = "assistant_messages"
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class AssistantToolCall(OwnedRecord, Base):
    __tablename__ = "assistant_tool_calls"
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("assistant_messages.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(40), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DocumentRightsReview(OwnedRecord, Base):
    __tablename__ = "document_rights_reviews"
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ResearchDocument(OwnedRecord, Base):
    __tablename__ = "research_documents"
    __table_args__ = (Index("ix_document_owner_cutoff", "user_id", "observed_at"),)
    instrument_id: Mapped[UUID | None] = mapped_column(ForeignKey("instruments.id"))
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    rights_review_id: Mapped[UUID | None] = mapped_column(ForeignKey("document_rights_reviews.id"))
    raw_ingestion_id: Mapped[UUID | None] = mapped_column(ForeignKey("raw_ingestions.id"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    object_key: Mapped[str | None] = mapped_column(String(300))
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("research_documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DocumentRemoval(OwnedRecord, Base):
    """Append-only withdrawal from the active library; raw audit evidence survives."""

    __tablename__ = "document_removals"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_removal_document"),)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("research_documents.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_version", name="uq_chunk_model"),
        Index(
            "ix_chunk_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("document_chunks.id"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(250), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AlertRule(OwnedRecord, Base):
    __tablename__ = "alert_rules"
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertRuleVersion(OwnedRecord, Base):
    __tablename__ = "alert_rule_versions"
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("alert_rules.id"), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class AlertEvaluation(OwnedRecord, Base):
    __tablename__ = "alert_evaluations"
    __table_args__ = (Index("ix_alert_evaluation_rule_created", "rule_id", "created_at"),)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("alert_rules.id"), nullable=False)
    rule_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("alert_rule_versions.id"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[bool | None] = mapped_column(Boolean)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class AlertEvent(OwnedRecord, Base):
    __tablename__ = "alert_events"
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("alert_rules.id"), nullable=False)
    evaluation_id: Mapped[UUID] = mapped_column(ForeignKey("alert_evaluations.id"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class Notification(OwnedRecord, Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "dedup_key", name="uq_notification_period"),)
    dedup_key: Mapped[str] = mapped_column(String(180), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DailyBriefConfig(Base):
    __tablename__ = "daily_brief_configs"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False, default="07:00")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Zurich")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DailyBrief(OwnedRecord, Base):
    __tablename__ = "daily_briefs"
    __table_args__ = (UniqueConstraint("user_id", "local_date", name="uq_brief_local_period"),)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class OptimizerRun(OwnedRecord, Base):
    __tablename__ = "optimizer_runs"
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    risk_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("risk_snapshots.id"), nullable=False)
    profile_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("investment_profile_versions.id")
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class FinancialEventVersion(OwnedRecord, Base):
    __tablename__ = "financial_event_versions"
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    replaces_id: Mapped[UUID | None] = mapped_column(ForeignKey("financial_event_versions.id"))
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
