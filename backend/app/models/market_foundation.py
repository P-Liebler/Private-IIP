from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "gate_status IN ('UNKNOWN', 'APPROVED', 'BLOCKED')", name="ck_source_gate_status"
        ),
        CheckConstraint("NOT enabled OR gate_status = 'APPROVED'", name="ck_source_enabled_gate"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(1), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gate_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    terms_url: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    allowed_uses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    decision_note: Mapped[str | None] = mapped_column(Text)
    decision_by: Mapped[str | None] = mapped_column(String(100))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        Index("ix_instruments_ticker", "ticker"),
        Index("ix_instruments_name", "name"),
        CheckConstraint("asset_type IN ('STOCK', 'ETF')", name="ck_instrument_asset_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticker: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(40))
    mic: Mapped[str | None] = mapped_column(String(10))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    isin: Mapped[str | None] = mapped_column(String(12))
    figi: Mapped[str | None] = mapped_column(String(12))
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    listed_at: Mapped[date | None] = mapped_column(Date)
    delisted_at: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RawIngestion(Base):
    __tablename__ = "raw_ingestions"
    __table_args__ = (
        Index("ix_raw_ingestions_source_received", "source_id", "received_at"),
        CheckConstraint("status IN ('PENDING', 'STORED', 'FAILED')", name="ck_raw_status"),
        CheckConstraint(
            "status <> 'STORED' OR (object_path IS NOT NULL AND sha256 IS NOT NULL)",
            name="ck_raw_stored_complete",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    instrument_id: Mapped[UUID | None] = mapped_column(ForeignKey("instruments.id"))
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    object_path: Mapped[str | None] = mapped_column(Text, unique=True)
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error: Mapped[str | None] = mapped_column(String(300))
    request_metadata: Mapped[dict[str, str | int]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstrumentIdentifier(Base):
    __tablename__ = "instrument_identifiers"
    __table_args__ = (
        CheckConstraint("type IN ('TICKER', 'ISIN', 'FIGI')", name="ck_identifier_type"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_identifier_dates"),
        Index("ix_identifier_lookup", "type", "value"),
        Index("ix_identifier_instrument", "instrument_id"),
        Index(
            "uq_identifier_current",
            "type",
            "value",
            "market_key",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[str] = mapped_column(String(40), nullable=False)
    market_key: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("data_sources.id"))
    raw_ingestion_id: Mapped[UUID | None] = mapped_column(ForeignKey("raw_ingestions.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
