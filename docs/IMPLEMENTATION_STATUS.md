# Implementation status

**Updated:** 2026-10-05
**Source of truth:** [Master Development Plan](../MASTER_DEVELOPMENT_PLAN.md), section 158. Assignment phases split the plan's foundation work into deliveries.

| Assignment phase | Plan mapping | Status | Delivered |
| --- | --- | --- | --- |
| Phase 0 — project foundation | P0 | DONE | Repository rules, local environment, Compose, architecture docs and ADRs. |
| Phase 1A — minimal core | P1 subset | DONE | Next.js, FastAPI health, shared settings/logging, request IDs, SQLAlchemy, Alembic and pgvector. |
| Phase 1B — data/background foundation | P1 subset | DONE | Valkey, Celery worker/Beat, MinIO adapter, health probes and smoke commands. |
| Phase 2 — authentication + core | P1 subset | DONE | Private CLI bootstrap, Argon2id, server-side sessions, TOTP, settings, audit trail, protected web routes and hourly session cleanup. |
| P1 raw-ingestion closure | P1 remaining scope | DONE | `raw_ingestions`, immutable MinIO object path, SHA-256 verification, provenance and manual CSV raw input. This was missing when Phase 2 was first marked done and was closed in this assignment. |
| Phase 3 — Instrument Master | P2 | DONE | Stable UUID instruments, dated identifiers, protected search/detail/create/update APIs, source rights gate and admin CLI, gated OpenFIGI mapping, CSV validation preview and minimal protected UI. |
| Phase 4 — Market Data Foundation | P3 | NOT STARTED | No Yahoo/Stooq price collector, canonical prices, FX or corporate actions. |
| Production access/observability | P4 gate | NOT STARTED | Caddy/TLS ingress, monitoring and backup/restore deployment remain future work. |

## P1/P2 verification

- `docker compose config --quiet` and `docker compose up -d --build` passed. All seven services reported healthy after rebuilding with the runtime `httpx` dependency.
- Existing Phase-2 database upgraded to `0003_raw_sources_instruments`. An empty temporary database upgraded from `0001` through `0003`; `users`, `sessions`, `audit_events`, `data_sources`, `instruments`, `instrument_identifiers` and `raw_ingestions` were confirmed, then the temporary database was removed. The existing auth tables and session data remained available.
- `docker compose exec -T api pytest -q`: **27 passed**, one upstream `StarletteDeprecationWarning`. P1/P2 tests cover raw bytes/hash/integrity/failure handling, metadata secrets, manual CSV, identifier history/conflicts/ambiguity, source approvals and shared rate limiting, OpenFIGI MockTransport responses and zero HTTP requests behind blocked/unknown gates, explicit mapping acceptance/provenance, protected APIs and CSV resolution. No test calls a live financial provider.
- `ruff check .`, `ruff format --check .`, `mypy app`, frontend `npm run lint`, `npm run typecheck` and `npm run build`: passed locally. The build includes `/instruments`, `/instrument/[id]` and `/settings/data-sources`.
- Celery and MinIO smoke commands passed. API readiness returned HTTP 200; anonymous protected web routes returned 307 to login; anonymous source API returned 401. Source CLI showed `MANUAL_CSV` approved/enabled, `YAHOO` blocked/disabled and `STOOQ`/`OPENFIGI` unknown/disabled.
- `.github/workflows/ci.yml` runs Compose-backed backend checks and frontend checks with an ephemeral TOTP key. **NOT VERIFIED REMOTELY**: no GitHub Actions run was available in this local assignment.

## Operational limits

- The local Compose setup uses HTTP and binds published ports to localhost. Production requires HTTPS, secure cookies, protected secret storage, controlled ingress, monitoring and tested backup/restore procedures.
- TOTP recovery is an administrative CLI reset; no email recovery or public registration exists. The Fernet key must be kept with protected backups.
- Python lockfiles pin versions but do not include artifact hashes. Review [ADR-010](decisions/ADR-010-minio-image.md) before production.
- P2 OpenFIGI is a gated mapping connector. It remains disabled without an explicit rights decision. Yahoo is blocked; Stooq is unreviewed. The CSV flow is a preview and creates no canonical prices. Assignment Phase 4 / normative P3 starts in a future task.
