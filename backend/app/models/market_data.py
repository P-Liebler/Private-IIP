from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceDailyVersion(Base):
    __tablename__ = "price_daily_versions"
    __table_args__ = (
        Index("ix_price_version_pit", "instrument_id", "trading_date", "known_at"),
        UniqueConstraint("raw_ingestion_id", "row_number", name="uq_price_raw_row"),
        CheckConstraint(
            "close > 0 AND (open IS NULL OR open > 0) "
            "AND (high IS NULL OR high > 0) AND (low IS NULL OR low > 0) "
            "AND (volume IS NULL OR volume >= 0)",
            name="ck_price_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    high: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    low: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(28, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=False)
    validation_version: Mapped[str] = mapped_column(String(30), nullable=False)
    reconciliation_version: Mapped[str] = mapped_column(String(30), nullable=False)
    replaces_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("price_daily_versions.id"))
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_label: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    resolution: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PriceDaily(Base):
    __tablename__ = "price_daily"
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    trading_date: Mapped[date] = mapped_column(Date, primary_key=True)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("price_daily_versions.id"), nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    high: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    low: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(28, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    primary_source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CorporateActionVersion(Base):
    __tablename__ = "corporate_action_versions"
    __table_args__ = (UniqueConstraint("raw_ingestion_id", "row_number", name="uq_action_raw_row"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    currency: Mapped[str | None] = mapped_column(String(3))
    new_ticker: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=False)
    validation_version: Mapped[str] = mapped_column(String(30), nullable=False)
    replaces_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("corporate_action_versions.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    action_date: Mapped[date] = mapped_column(Date, primary_key=True)
    action_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_action_versions.id"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)


class FxRateVersion(Base):
    __tablename__ = "fx_rate_versions"
    __table_args__ = (
        UniqueConstraint("raw_ingestion_id", "row_number", name="uq_fx_raw_row"),
        CheckConstraint("rate > 0", name="ck_fx_positive"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    fixing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(30), nullable=False)
    validation_version: Mapped[str] = mapped_column(String(30), nullable=False)
    replaces_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("fx_rate_versions.id"))
    resolution: Mapped[str] = mapped_column(String(30), nullable=False, default="ACCEPTED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FxRate(Base):
    __tablename__ = "fx_rates"
    base_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    quote_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_date: Mapped[date] = mapped_column(Date, primary_key=True)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("fx_rate_versions.id"), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DataQuarantine(Base):
    __tablename__ = "data_quarantine"
    __table_args__ = (
        UniqueConstraint(
            "raw_ingestion_id", "row_number", "data_type", name="uq_quarantine_raw_row"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    raw_ingestion_id: Mapped[UUID] = mapped_column(ForeignKey("raw_ingestions.id"), nullable=False)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    instrument_id: Mapped[UUID | None] = mapped_column(ForeignKey("instruments.id"))
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    record_key: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    row_data: Mapped[dict[str, str | None]] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
