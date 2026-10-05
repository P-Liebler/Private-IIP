# Implementation status

**Updated:** 2026-10-05
**Source of truth:** [Master Development Plan](../MASTER_DEVELOPMENT_PLAN.md), section 158. The assignment names below split the plan's foundation and authentication work into delivery phases.

| Assignment phase | Plan mapping | Status | Delivered |
| --- | --- | --- | --- |
| Phase 0 — project foundation | P0 | DONE | Repository rules, local environment, Compose, architecture docs and ADRs. |
| Phase 1A — minimal core | P1 subset | DONE | Next.js, FastAPI health, shared settings/logging, request IDs, SQLAlchemy, Alembic and pgvector. |
| Phase 1B — data/background foundation | P1 subset | DONE | Valkey, Celery worker/Beat, MinIO adapter, health probes and smoke commands. |
| Phase 2 — Authentication + Core | P1 remaining scope | DONE | Private CLI bootstrap, Argon2id, server-side sessions, TOTP, settings, audit trail, protected web routes and hourly session cleanup. |
| Phase 3 — Instrument Master | P2 | NOT STARTED | No instruments, identifiers or OpenFIGI integration. |
| Phase 4 — Market Data Foundation | P3 | NOT STARTED | No collectors, prices or corporate actions. |
| Production access/observability | P4 gate | NOT STARTED | Caddy, TLS ingress, monitoring and backup/restore deployment remain future work. |

## Phase 2 verification

- `docker compose config --quiet` and `docker compose up -d --build`: passed; all seven services were healthy at the last smoke test.
- `docker compose exec -T api alembic upgrade head`: passed. A separate empty database upgraded through revisions `0001_enable_pgvector` and `0002_auth_core`; `users`, `sessions` and `audit_events` were confirmed, then the temporary database was removed.
- `docker compose exec -T api pytest -q`: 20 passed, one upstream `StarletteDeprecationWarning` from `fastapi.testclient`. PostgreSQL/Valkey integration tests cover the real admin CLI, account creation, login, cookie/session expiry, rate limit, settings, CSRF, TOTP setup/verification, logout, reset, audit fields and inactive-user handling.
- `docker compose exec -T api ruff check .`, `ruff format --check .`, `mypy app`: passed in the last completed checks.
- `npm run lint`, `npm run typecheck`, `npm run build` in `frontend/web`: passed in the last completed checks. Build includes dynamic protected `/dashboard` and `/settings` routes.
- Live smoke: `/login` returned HTTP 200, anonymous `/dashboard` redirected (307), API readiness returned HTTP 200; Celery and MinIO smoke tests passed.

## Operational limits

- The local Compose setup uses HTTP and binds published ports to localhost. Production requires HTTPS, a secure cookie, protected secret storage, controlled ingress, monitoring and tested backup/restore procedures.
- TOTP recovery is an administrative CLI reset; no email recovery or public registration exists. The Fernet key must be kept with protected backups; loss of it makes enrolled TOTP secrets unusable.
- Python lockfiles pin versions but do not include artifact hashes. The MinIO image is a community build of the October 2025 upstream release; review [ADR-010](decisions/ADR-010-minio-image.md) before production.
- Financial data, portfolio calculations, ML and assistant features have not started. The next development work is Phase 3 Instrument Master, followed by Phase 4 Market Data Foundation.
