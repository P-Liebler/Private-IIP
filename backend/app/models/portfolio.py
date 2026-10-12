from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(
        ForeignKey("instruments.id"), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolios_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CHF")
    benchmark_id: Mapped[UUID | None] = mapped_column(ForeignKey("benchmarks.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PortfolioAccount(Base):
    __tablename__ = "portfolio_accounts"
    __table_args__ = (Index("ix_portfolio_accounts_portfolio", "portfolio_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    default_currency: Mapped[str | None] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_portfolio_date", "portfolio_id", "trade_date"),
        Index("ix_transactions_account_external", "account_id", "external_id"),
        Index("ix_transactions_fingerprint", "account_id", "fingerprint"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False)
    instrument_id: Mapped[UUID | None] = mapped_column(ForeignKey("instruments.id"))
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal(0))
    tax: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal(0))
    fx_rate_to_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    external_id: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="ACTIVE")
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    replaces_transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"))
    corporate_action_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("corporate_action_versions.id")
    )
    raw_ingestion_id: Mapped[UUID | None] = mapped_column(ForeignKey("raw_ingestions.id"))
    system_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PortfolioActionApplication(Base):
    __tablename__ = "portfolio_action_applications"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "instrument_id",
            "action_date",
            "action_type",
            name="uq_portfolio_action_application",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    action_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("corporate_action_versions.id"), nullable=False
    )
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"))
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CashBalance(Base):
    __tablename__ = "cash_balances"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "account_id",
            "currency",
            "snapshot_date",
            "input_hash",
            name="uq_cash_snapshot_input",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PositionSnapshot(Base):
    __tablename__ = "position_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "account_id",
            "instrument_id",
            "snapshot_date",
            "input_hash",
            name="uq_position_snapshot_input",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    market_value_native: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    market_value_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    valuation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    price_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("price_daily_versions.id"))
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "snapshot_date", "input_hash", name="uq_portfolio_snapshot_input"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cash_value_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    securities_value_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    total_value_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    cost_basis_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    realized_pnl_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    unrealized_pnl_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    income_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    fees_base: Mapped[Decimal | None] = mapped_column(Numeric(28, 8))
    completeness_status: Mapped[str] = mapped_column(String(20), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_cutoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_provenance: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
