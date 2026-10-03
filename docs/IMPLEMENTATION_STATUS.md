# Implementation status

**Updated:** 2026-10-03  
**Source of truth:** [Master Development Plan](../MASTER_DEVELOPMENT_PLAN.md), section 158. This assignment calls the foundation slices **Phase 0**, **Phase 1A** and **Phase 1B**. The masterplan groups them in P0/P1 and also places future authentication in P1; the current user instruction explicitly defers authentication.

| Assignment slice | Masterplan mapping | Status | Delivered |
| --- | --- | --- | --- |
| Phase 0 — project foundation | P0 | DONE | Repository rules, README, local environment, Compose, architecture docs and ADRs. |
| Phase 1A — minimal core | P1 subset | DONE | Next.js status page, typed API client, FastAPI health API, settings, logs, request IDs, SQLAlchemy, Alembic and pgvector. |
| Phase 1B — data/background foundation | P1 subset | DONE | Valkey, Celery worker and Beat, MinIO storage adapter, health probes and smoke commands. |
| Phase 1C — access/observability | P4 production gate | NOT STARTED | Caddy, Prometheus, Grafana and production access belong to later work. |
| Authentication + Core | P1 remaining work | NOT STARTED | Users, sessions, Argon2id, TOTP, settings and audit domain are the next assignment. |
| Instrument/data pipeline onward | P2–P10 | NOT STARTED | No collectors or financial data are implemented. |

## Validation performed

- `docker compose config --quiet`: passed.
- `docker compose --progress quiet up --build -d`: all seven services started; `docker compose ps` showed each as healthy.
- `docker compose exec -T api alembic upgrade head`: passed. PostgreSQL reported pgvector extension `0.8.6`.
- `docker compose exec -T api pytest -q`: **13 passed** (10 unit, 3 integration). One upstream `StarletteDeprecationWarning` from `fastapi.testclient` remains.
- `docker compose exec -T api ruff check .`, `ruff format --check .`, and `mypy app`: passed.
- `npm run lint`, `npm run typecheck`, and `npm run build` in `frontend/web`: passed. The built web page returned HTTP 200 with the heading and status area; the Compose web container was healthy. Both production Docker targets built; the standalone web image also served HTTP 200 on a temporary local port.
- API readiness returned HTTP 200 with database, Valkey and MinIO `ok`, and echoed a valid `X-Request-ID`. With MinIO deliberately stopped, it returned HTTP 503 with only MinIO `unavailable`; after restart it returned HTTP 200 again.
- `python -m app.jobs.smoke`: Celery task completed through Valkey and worker. `python -m app.core.storage_smoke`: MinIO put/head/get/delete round trip passed.
- The 56 packages installed in the API container exactly match the combined Python lockfiles.

## Limitations and next work

- This is a localhost development foundation. It has no authentication, collector, financial data, portfolio calculation, backup/restore automation or production ingress. Do not expose its API or status page publicly.
- The pinned MinIO image is a community build of the October 2025 upstream release. Its provenance and maintenance must be reviewed again before production use; see [ADR-010](decisions/ADR-010-minio-image.md).
- Python runtime and development dependencies, including transitives, are version pinned in `backend/requirements.lock` and `backend/requirements-dev.lock`; the frontend has a committed npm lockfile. The Python locks pin versions but do not include artifact hashes.
- The harmless Celery Beat schedule is empty. The next development assignment is **Authentication + Core**; it was not started here.
