"""Technical retry receipts, separate from immutable financial observations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UIRequest(Base):
    __tablename__ = "ui_requests"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    request_id: Mapped[UUID] = mapped_column(primary_key=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
