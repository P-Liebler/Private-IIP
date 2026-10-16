from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            error_type = record.exc_info[0]
            if error_type is not None:
                payload["error_type"] = error_type.__name__
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # FRED credentials may be query parameters. Never emit HTTP URL/debug logs.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).disabled = True
    for name in ("uvicorn.access", "uvicorn.error", "celery"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
