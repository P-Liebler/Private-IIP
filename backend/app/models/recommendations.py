from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvestmentProfileVersion(Base):
    __tablename__ = "investment_profile_versions"
    __table_args__ = (Index("ix_profile_user_created", "user_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_id: Mapped[UUID | None] = mapped_column(ForeignKey("investment_profile_versions.id"))
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecommendationRuleVersion(Base):
    __tablename__ = "recommendation_rule_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendation_user_created", "user_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    portfolio_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolio_snapshots.id"), nullable=False
    )
    risk_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("risk_snapshots.id"), nullable=False)
    prediction_id: Mapped[UUID | None] = mapped_column(ForeignKey("predictions.id"))
    research_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("research_snapshots.id"))
    profile_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_profile_versions.id"), nullable=False
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_rule_versions.id"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecommendationBacktest(Base):
    __tablename__ = "recommendation_backtests"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    rule_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_rule_versions.id"), nullable=False
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecommendationStrategyReview(Base):
    __tablename__ = "recommendation_strategy_reviews"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    rule_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_rule_versions.id"), nullable=False
    )
    backtest_id: Mapped[UUID] = mapped_column(ForeignKey("recommendation_backtests.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
