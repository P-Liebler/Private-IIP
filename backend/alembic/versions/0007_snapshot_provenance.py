"""Preserve snapshot knowledge cutoff and exact dependency references.

Revision ID: 0007_snapshot_provenance
Revises: 0006_portfolio
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_snapshot_provenance"
down_revision: str | None = "0006_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing snapshots keep unknown provenance explicit; never infer an old cutoff.
    op.add_column("portfolio_snapshots", sa.Column("knowledge_cutoff", sa.DateTime(timezone=True)))
    op.add_column("portfolio_snapshots", sa.Column("input_provenance", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("portfolio_snapshots", "input_provenance")
    op.drop_column("portfolio_snapshots", "knowledge_cutoff")
