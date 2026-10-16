from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
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


class AvailabilityReview(Base):
    __tablename__ = "availability_reviews"
    __table_args__ = (
        Index("ix_availability_target", "entity_type", "entity_id", "created_at"),
        CheckConstraint(
            "level IN ('VERIFIED_PUBLIC_TIMESTAMP', 'VERIFIED_SOURCE_DOCUMENT', "
            "'LOCAL_FIRST_OBSERVATION', 'USER_ASSERTED', 'UNVERIFIED')",
            name="ck_availability_level",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UniverseDefinition(Base):
    __tablename__ = "universe_definitions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UniverseMembershipVersion(Base):
    __tablename__ = "universe_membership_versions"
    __table_args__ = (
        UniqueConstraint("universe_id", "raw_ingestion_id", "row_key", name="uq_universe_raw_key"),
        Index("ix_membership_pit", "universe_id", "instrument_id", "observed_at"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from", name="ck_membership_interval"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universe_definitions.id"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    membership_status: Mapped[str] = mapped_column(String(20), nullable=False)
    row_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    replaces_id: Mapped[UUID | None] = mapped_column(ForeignKey("universe_membership_versions.id"))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ActionCoverageReview(Base):
    __tablename__ = "action_coverage_reviews"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_coverage_interval"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_version_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    action_types: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: ["SPLIT", "DIVIDEND"],
        server_default='["SPLIT", "DIVIDEND"]',
    )
    coverage_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        UniqueConstraint("instrument_id", "content_hash", name="uq_feature_identity"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    information_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("user_id", "content_hash", name="uq_dataset_identity"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universe_definitions.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    quality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MacroObservation(Base):
    __tablename__ = "macro_observation_versions"
    __table_args__ = (UniqueConstraint("raw_ingestion_id", "row_key", name="uq_macro_raw_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    series: Mapped[str] = mapped_column(String(40), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(10))
    provider_series: Mapped[str | None] = mapped_column(String(100))
    release_date: Mapped[date | None] = mapped_column(Date)
    revision_type: Mapped[str | None] = mapped_column(String(40))
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    row_key: Mapped[str] = mapped_column(String(64), nullable=False)
    replaces_id: Mapped[UUID | None] = mapped_column(ForeignKey("macro_observation_versions.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WalkForwardSplit(Base):
    __tablename__ = "walk_forward_splits"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NewsMappingVersion(Base):
    __tablename__ = "news_mapping_versions"
    __table_args__ = (
        UniqueConstraint(
            "article_id", "instrument_id", "observed_at", name="uq_news_mapping_version"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
    )
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PITJob(Base):
    __tablename__ = "pit_jobs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
