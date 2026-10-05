"""Add raw provenance, source gates, and instrument identity.

Revision ID: 0003_raw_sources_instruments
Revises: 0002_auth_core
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_raw_sources_instruments"
down_revision = "0002_auth_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("trust_level", sa.String(1), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rate_limit_per_minute", sa.Integer()),
        sa.Column("last_success", sa.DateTime(timezone=True)),
        sa.Column("last_failure", sa.DateTime(timezone=True)),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gate_status", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("terms_url", sa.Text()),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("scope", sa.Text()),
        sa.Column(
            "allowed_uses",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("decision_note", sa.Text()),
        sa.Column("decision_by", sa.String(100)),
        sa.Column("next_review_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "gate_status IN ('UNKNOWN', 'APPROVED', 'BLOCKED')", name="ck_source_gate_status"
        ),
        sa.CheckConstraint(
            "NOT enabled OR gate_status = 'APPROVED'", name="ck_source_enabled_gate"
        ),
    )
    source_table = sa.table(
        "data_sources",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("type", sa.String()),
        sa.column("trust_level", sa.String()),
        sa.column("priority", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("gate_status", sa.String()),
        sa.column("checked_at", sa.DateTime(timezone=True)),
        sa.column("scope", sa.Text()),
        sa.column("allowed_uses", postgresql.JSONB()),
        sa.column("decision_note", sa.Text()),
        sa.column("decision_by", sa.String()),
    )
    observed = datetime.now(UTC)
    seed = [
        (
            "MANUAL_CSV",
            "Manual CSV",
            "MANUAL",
            "D",
            10,
            True,
            "APPROVED",
            observed,
            "Files supplied by the authenticated user only",
            ["manual_upload"],
            "Local user-supplied files; no external retrieval",
            "system_bootstrap",
        ),
        (
            "OPENFIGI",
            "OpenFIGI",
            "IDENTIFIER_API",
            "B",
            20,
            False,
            "UNKNOWN",
            None,
            None,
            [],
            None,
            None,
        ),
        (
            "YAHOO",
            "Yahoo Finance",
            "AGGREGATOR",
            "B",
            30,
            False,
            "BLOCKED",
            None,
            None,
            [],
            "Automated access requires documented permission",
            "system_bootstrap",
        ),
        ("STOOQ", "Stooq", "AGGREGATOR", "B", 40, False, "UNKNOWN", None, None, [], None, None),
    ]
    op.bulk_insert(
        source_table,
        [
            {
                "id": uuid5(NAMESPACE_URL, f"private-iip/source/{slug}"),
                "slug": slug,
                "name": name,
                "type": source_type,
                "trust_level": trust,
                "priority": priority,
                "enabled": enabled,
                "gate_status": gate,
                "checked_at": checked,
                "scope": scope,
                "allowed_uses": uses,
                "decision_note": note,
                "decision_by": reviewer,
            }
            for (
                slug,
                name,
                source_type,
                trust,
                priority,
                enabled,
                gate,
                checked,
                scope,
                uses,
                note,
                reviewer,
            ) in seed
        ],
    )
    op.create_table(
        "instruments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("ticker", sa.String(40)),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(40)),
        sa.Column("mic", sa.String(10)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country", sa.String(2)),
        sa.Column("isin", sa.String(12)),
        sa.Column("figi", sa.String(12)),
        sa.Column("sector", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("listed_at", sa.Date()),
        sa.Column("delisted_at", sa.Date()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("asset_type IN ('STOCK', 'ETF')", name="ck_instrument_asset_type"),
    )
    op.create_index("ix_instruments_ticker", "instruments", ["ticker"])
    op.create_index("ix_instruments_name", "instruments", ["name"])
    op.create_table(
        "raw_ingestions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("source_id", sa.UUID(), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("instrument_id", sa.UUID(), sa.ForeignKey("instruments.id")),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("object_path", sa.Text(), unique=True),
        sa.Column("sha256", sa.String(64)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("http_status", sa.Integer()),
        sa.Column("content_type", sa.String(150)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.String(300)),
        sa.Column(
            "request_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("status IN ('PENDING', 'STORED', 'FAILED')", name="ck_raw_status"),
        sa.CheckConstraint(
            "status <> 'STORED' OR (object_path IS NOT NULL AND sha256 IS NOT NULL)",
            name="ck_raw_stored_complete",
        ),
    )
    op.create_index(
        "ix_raw_ingestions_source_received", "raw_ingestions", ["source_id", "received_at"]
    )
    op.create_table(
        "instrument_identifiers",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.UUID(),
            sa.ForeignKey("instruments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("value", sa.String(40), nullable=False),
        sa.Column("market_key", sa.String(40), nullable=False, server_default=""),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date()),
        sa.Column("source_id", sa.UUID(), sa.ForeignKey("data_sources.id")),
        sa.Column("raw_ingestion_id", sa.UUID(), sa.ForeignKey("raw_ingestions.id")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("type IN ('TICKER', 'ISIN', 'FIGI')", name="ck_identifier_type"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_identifier_dates"),
    )
    op.create_index("ix_identifier_lookup", "instrument_identifiers", ["type", "value"])
    op.create_index("ix_identifier_instrument", "instrument_identifiers", ["instrument_id"])
    op.create_index(
        "uq_identifier_current",
        "instrument_identifiers",
        ["type", "value", "market_key"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("instrument_identifiers")
    op.drop_table("raw_ingestions")
    op.drop_table("instruments")
    op.drop_table("data_sources")
