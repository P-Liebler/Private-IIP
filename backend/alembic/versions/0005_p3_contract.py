"""Complete the P3 canonical contract and FX acceptance state.

Revision ID: 0005_p3_contract
Revises: 0004_market_data
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_p3_contract"
down_revision = "0004_market_data"
branch_labels = None
depends_on = None


def add(table: str, *columns: sa.Column) -> None:
    for column in columns:
        op.add_column(table, column)


def upgrade() -> None:
    add(
        "price_daily_versions",
        sa.Column("adjusted_close", sa.Numeric(24, 8)),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
    )
    op.alter_column(
        "price_daily_versions",
        "quality_score",
        type_=sa.Float(),
        postgresql_using="quality_score::float / 100",
    )
    add(
        "price_daily",
        sa.Column("open", sa.Numeric(24, 8)),
        sa.Column("high", sa.Numeric(24, 8)),
        sa.Column("low", sa.Numeric(24, 8)),
        sa.Column("close", sa.Numeric(24, 8)),
        sa.Column("adjusted_close", sa.Numeric(24, 8)),
        sa.Column("volume", sa.Numeric(28, 4)),
        sa.Column("currency", sa.String(3)),
        sa.Column("primary_source_id", sa.Uuid(), sa.ForeignKey("data_sources.id")),
        sa.Column("source_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
        sa.Column("quality_score", sa.Float()),
        sa.Column("quality_components", postgresql.JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute(
        "UPDATE price_daily p SET open=v.open, high=v.high, low=v.low, close=v.close, "
        "volume=v.volume, currency=v.currency, primary_source_id=v.source_id, "
        "quality_score=v.quality_score, quality_components=v.quality_components "
        "FROM price_daily_versions v WHERE p.version_id=v.id"
    )
    for name in ("close", "currency", "primary_source_id", "quality_score", "quality_components"):
        op.alter_column("price_daily", name, nullable=False)
    add(
        "corporate_action_versions",
        sa.Column("record_date", sa.Date()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("ratio", sa.Numeric(24, 8)),
        sa.Column("cash_amount", sa.Numeric(24, 8)),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column(
            "quality_components",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute(
        "UPDATE corporate_action_versions SET ratio=value "
        "WHERE action_type IN ('SPLIT', 'REVERSE_SPLIT')"
    )
    op.execute(
        "UPDATE corporate_action_versions SET cash_amount=value WHERE action_type='DIVIDEND'"
    )
    add(
        "corporate_actions",
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("data_sources.id")),
        sa.Column("raw_ingestion_id", sa.Uuid(), sa.ForeignKey("raw_ingestions.id")),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
        sa.Column("quality_score", sa.Float()),
        sa.Column("quality_components", postgresql.JSONB()),
    )
    op.execute(
        "UPDATE corporate_actions c SET source_id=v.source_id, "
        "raw_ingestion_id=v.raw_ingestion_id, quality_score=v.quality_score, "
        "quality_components=v.quality_components FROM corporate_action_versions v "
        "WHERE c.version_id=v.id"
    )
    for name in ("source_id", "raw_ingestion_id", "quality_score", "quality_components"):
        op.alter_column("corporate_actions", name, nullable=False)
    add(
        "fx_rate_versions",
        sa.Column("fixing_at", sa.DateTime(timezone=True)),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column(
            "quality_components",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("resolution", sa.String(30), server_default="ACCEPTED", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    add(
        "fx_rates",
        sa.Column("rate", sa.Numeric(28, 12)),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("data_sources.id")),
        sa.Column("raw_ingestion_id", sa.Uuid(), sa.ForeignKey("raw_ingestions.id")),
        sa.Column("validation_status", sa.String(20), server_default="VALID", nullable=False),
        sa.Column("quality_score", sa.Float()),
        sa.Column("quality_components", postgresql.JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute(
        "UPDATE fx_rates f SET rate=v.rate, source_id=v.source_id, "
        "raw_ingestion_id=v.raw_ingestion_id, quality_score=v.quality_score, "
        "quality_components=v.quality_components FROM fx_rate_versions v "
        "WHERE f.version_id=v.id"
    )
    for name in ("rate", "source_id", "raw_ingestion_id", "quality_score", "quality_components"):
        op.alter_column("fx_rates", name, nullable=False)
    add(
        "data_quarantine",
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("data_sources.id")),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id")),
        sa.Column("record_key", sa.String(200), server_default="UNKNOWN", nullable=False),
        sa.Column("severity", sa.String(20), server_default="REJECTED", nullable=False),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution", sa.String(30)),
    )
    op.execute(
        "UPDATE data_quarantine q SET source_id=r.source_id "
        "FROM raw_ingestions r WHERE q.raw_ingestion_id=r.id"
    )
    op.alter_column("data_quarantine", "source_id", nullable=False)


def downgrade() -> None:
    for table, columns in (
        (
            "data_quarantine",
            (
                "resolution",
                "resolved_at",
                "detected_at",
                "severity",
                "record_key",
                "instrument_id",
                "source_id",
            ),
        ),
        (
            "fx_rates",
            (
                "updated_at",
                "created_at",
                "quality_components",
                "quality_score",
                "validation_status",
                "raw_ingestion_id",
                "source_id",
                "rate",
            ),
        ),
        (
            "fx_rate_versions",
            (
                "created_at",
                "resolution",
                "quality_components",
                "quality_score",
                "validation_status",
                "retrieved_at",
                "fixing_at",
            ),
        ),
        (
            "corporate_actions",
            (
                "quality_components",
                "quality_score",
                "validation_status",
                "raw_ingestion_id",
                "source_id",
            ),
        ),
        (
            "corporate_action_versions",
            (
                "created_at",
                "quality_components",
                "quality_score",
                "validation_status",
                "retrieved_at",
                "cash_amount",
                "ratio",
                "payment_date",
                "record_date",
            ),
        ),
        (
            "price_daily",
            (
                "updated_at",
                "created_at",
                "quality_components",
                "quality_score",
                "validation_status",
                "source_count",
                "primary_source_id",
                "currency",
                "volume",
                "adjusted_close",
                "close",
                "low",
                "high",
                "open",
            ),
        ),
        ("price_daily_versions", ("validation_status", "retrieved_at", "adjusted_close")),
    ):
        for column in columns:
            op.drop_column(table, column)
    op.alter_column(
        "price_daily_versions",
        "quality_score",
        type_=sa.Integer(),
        postgresql_using="round(quality_score * 100)::integer",
    )
