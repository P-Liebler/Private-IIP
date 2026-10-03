from __future__ import annotations

from app.jobs.celery_app import celery_app


def main() -> None:
    result = celery_app.send_task("system.ping")
    payload = result.get(timeout=20)
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise RuntimeError(f"Unexpected Celery result: {payload!r}")
    print(f"Celery task {result.id}: ok")


if __name__ == "__main__":
    main()
