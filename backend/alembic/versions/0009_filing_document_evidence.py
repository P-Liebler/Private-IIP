"""Distinguish response hashes from downloaded primary document hashes."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_filing_document"
down_revision: str | None = "0008_research"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preserve every previously recorded metadata response hash under its exact meaning.
    op.alter_column("filings", "document_hash", new_column_name="response_hash")
    op.add_column("filings", sa.Column("document_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("filings", "document_hash")
    op.alter_column("filings", "response_hash", new_column_name="document_hash")
