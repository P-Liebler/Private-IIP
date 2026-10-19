"""PR2 orchestration evidence; existing financial/model archives stay authoritative."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ValidationRecord(Base):
    __tablename__ = "validation_records"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "dedup_key", name="uq_validation_dedup"),
        Index("ix_validation_user_kind_created", "user_id", "kind", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("validation_records.id"))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(64))
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
