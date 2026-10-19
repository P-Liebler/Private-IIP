"""Append-only PR2 coordination evidence, without changing pinned P6 rows."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019_validation"
down_revision = "0018_provider_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("validation_records.id")),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("dedup_key", sa.String(64)),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "kind", "dedup_key", name="uq_validation_dedup"),
    )
    op.create_index(
        "ix_validation_user_kind_created", "validation_records", ["user_id", "kind", "created_at"]
    )
    op.execute(
        "CREATE TRIGGER validation_records_immutable BEFORE UPDATE ON validation_records "
        "FOR EACH ROW EXECUTE FUNCTION reject_pit_update()"
    )


def downgrade() -> None:
    op.drop_table("validation_records")
