"""P5 immutable evidence and versioned research read models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import utc_now


class Evidence:
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class Filing(Evidence, Base):
    __tablename__ = "filings"
    __table_args__ = (
        UniqueConstraint("instrument_id", "source_id", "accession_number", "raw_ingestion_id"),
        Index("ix_filings_instrument_known", "instrument_id", "known_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    accession_number: Mapped[str] = mapped_column(String(100))
    filing_type: Mapped[str] = mapped_column(String(30))
    filing_date: Mapped[date] = mapped_column(Date)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[date] = mapped_column(Date)
    document_url: Mapped[str | None] = mapped_column(Text)
    response_hash: Mapped[str] = mapped_column(String(64))
    document_hash: Mapped[str | None] = mapped_column(String(64))
    availability_evidence: Mapped[str] = mapped_column(Text)


class FundamentalFact(Evidence, Base):
    __tablename__ = "fundamental_fact_versions"
    __table_args__ = (
        UniqueConstraint("raw_ingestion_id", "row_key"),
        Index("ix_facts_pit", "instrument_id", "metric", "period_end", "known_at", "observed_at"),
        CheckConstraint(
            "validation_status IN ('VALID','WARNING','REJECTED')", name="ck_fact_validation"
        ),
        CheckConstraint(
            "period_start IS NULL OR period_start <= period_end", name="ck_fact_period"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    metric: Mapped[str] = mapped_column(String(60))
    value: Mapped[Decimal | None] = mapped_column(Numeric(38, 12))
    unit: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str | None] = mapped_column(String(3))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    period_type: Mapped[str] = mapped_column(String(20))
    fiscal_year: Mapped[int | None]
    fiscal_quarter: Mapped[int | None]
    filing_id: Mapped[UUID | None] = mapped_column(ForeignKey("filings.id"))
    row_key: Mapped[str] = mapped_column(String(64))
    validation_status: Mapped[str] = mapped_column(String(20))
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    quality_components: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    parser_version: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[str] = mapped_column(String(40))
    replaces_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fundamental_fact_versions.id")
    )
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class ResearchSnapshot(Base):
    __tablename__ = "research_snapshots"
    __table_args__ = (
        UniqueConstraint("instrument_id", "input_hash"),
        Index("ix_research_pit", "instrument_id", "as_of"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rule_version: Mapped[str] = mapped_column(String(40))
    input_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class ResearchMetric(Base):
    __tablename__ = "research_metrics"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "metric"),
        Index("ix_research_metric_filter", "metric", "value"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("research_snapshots.id"))
    metric: Mapped[str] = mapped_column(String(60))
    value: Mapped[Decimal | None] = mapped_column(Numeric(38, 12))
    status: Mapped[str] = mapped_column(String(30))


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now()
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "instrument_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    watchlist_id: Mapped[UUID] = mapped_column(ForeignKey("watchlists.id"))
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class NewsArticle(Evidence, Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("raw_ingestion_id", "row_key"),
        Index("ix_news_pit", "known_at", "observed_at"),
        Index("ix_news_url", "url_hash"),
        Index("ix_news_content", "content_hash"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(1000))
    summary: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(12))
    row_key: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    url_hash: Mapped[str] = mapped_column(String(64))
    duplicate_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("news_articles.id"))
    sentiment: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class NewsInstrument(Base):
    __tablename__ = "news_instruments"
    __table_args__ = (UniqueConstraint("article_id", "instrument_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("news_articles.id"))
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    entity_confidence: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    mapping_status: Mapped[str] = mapped_column(String(30))


class AnalystEstimate(Evidence, Base):
    __tablename__ = "analyst_estimate_snapshots"
    __table_args__ = (
        UniqueConstraint("raw_ingestion_id", "row_key"),
        Index("ix_estimates_pit", "instrument_id", "estimate_type", "observed_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    estimate_type: Mapped[str] = mapped_column(String(40))
    target_period: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 12))
    unit: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str | None] = mapped_column(String(3))
    row_key: Mapped[str] = mapped_column(String(64))
    quality: Mapped[dict[str, object]] = mapped_column(JSONB)
    replaces_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analyst_estimate_snapshots.id")
    )
    rule_version: Mapped[str] = mapped_column(String(40))
