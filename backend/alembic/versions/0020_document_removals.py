"""Append-only removal decisions without deleting immutable source originals."""

import sqlalchemy as sa

from alembic import op

revision = "0020_document_removals"
down_revision = "0019_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_removals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("research_documents.id"), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("document_id", name="uq_document_removal_document"),
    )
    op.execute(
        "CREATE TRIGGER document_removals_immutable BEFORE UPDATE OR DELETE ON document_removals "
        "FOR EACH ROW EXECUTE FUNCTION reject_pit_update()"
    )


def downgrade() -> None:
    # Only an explicit schema downgrade removes removal decisions. No automatic downgrade.
    op.drop_table("document_removals")
