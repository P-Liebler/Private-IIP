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
    include=["app.jobs.tasks", "app.jobs.ml", "app.jobs.intelligence"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "local-intelligence-dispatch": {"task": "intelligence.dispatch", "schedule": 60.0},
        "private-chat-retention": {"task": "assistant.cleanup_chats", "schedule": 3600.0},
        "cleanup-expired-sessions": {
            "task": "auth.cleanup_sessions",
            "schedule": 3600.0,
        },
        "approved-research-collection": {
            "task": "research.collect_approved",
            "schedule": 86400.0,
        },
    },
)
