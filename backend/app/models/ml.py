from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MLTrainingRun(Base):
    __tablename__ = "ml_training_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')",
            name="ck_ml_job_status",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="ck_ml_job_progress"),
        Index("ix_ml_jobs_user_created", "user_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    celery_task_id: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"
    __table_args__ = (Index("ix_ml_models_user_created", "user_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ml_training_runs.id"), nullable=False, unique=True
    )
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(180), nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ModelPromotionReview(Base):
    __tablename__ = "model_promotion_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('EXPERIMENT','VALIDATION','SHADOW','PRODUCTION','RETIRED')",
            name="ck_ml_review_status",
        ),
        Index("ix_ml_reviews_model_created", "model_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_id: Mapped[UUID] = mapped_column(ForeignKey("ml_model_versions.id"), nullable=False)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_user_instrument_created", "user_id", "instrument_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    model_id: Mapped[UUID | None] = mapped_column(ForeignKey("ml_model_versions.id"))
    dataset_id: Mapped[UUID | None] = mapped_column(ForeignKey("dataset_versions.id"))
    feature_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("feature_snapshots.id"))
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    information_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    __table_args__ = (Index("ix_outcomes_prediction_created", "prediction_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    prediction_id: Mapped[UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    replaces_id: Mapped[UUID | None] = mapped_column(ForeignKey("prediction_outcomes.id"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
