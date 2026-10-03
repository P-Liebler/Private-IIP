"""Enable pgvector for future embedding migrations.

Revision ID: 0001_enable_pgvector
Revises:
"""

from alembic import op

revision = "0001_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Extensions may be used by later migrations; do not drop it automatically.
    pass
