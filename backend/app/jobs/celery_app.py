from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()
celery_app = Celery(
    "investment_intelligence",
    broker=settings.valkey_url,
    backend=settings.valkey_url,
    include=["app.jobs.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "auth.cleanup_sessions",
            "schedule": 3600.0,
        },
    },
)
