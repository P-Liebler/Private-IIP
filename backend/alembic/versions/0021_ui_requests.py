"""Atomic retry receipts for UI resource creation, without changing financial rows."""

import sqlalchemy as sa

from alembic import op

revision = "0021_ui_requests"
down_revision = "0020_document_removals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ui_requests",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("request_id", sa.Uuid(), primary_key=True),
        sa.Column("operation", sa.String(120), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute(
        "CREATE TRIGGER ui_requests_immutable BEFORE UPDATE OR DELETE ON ui_requests "
        "FOR EACH ROW EXECUTE FUNCTION reject_pit_update()"
    )


def downgrade() -> None:
    op.drop_table("ui_requests")
