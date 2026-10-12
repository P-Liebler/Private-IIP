# Private Investment Intelligence Platform

Self-hosted investment research and portfolio platform, built in phases toward the architecture in [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md). This repository includes **P1 raw ingestion, P2 instrument identity/source gates and P3 market-data foundation**. Manual CSV import supplies validated prices, corporate actions and FX; portfolio accounting and forecasts follow in later phases.

## Current architecture

| Service | Purpose | Local address |
| --- | --- | --- |
| Next.js `web` | Login, instruments, CSV import, data quality and settings | http://localhost:3000 |
| FastAPI `api` | Health, authentication, instruments, sources and P3 market-data API | http://localhost:8000 |
| PostgreSQL + pgvector `postgres` | Alembic-managed database | Internal Compose network |
| Valkey `valkey` | Celery broker and result backend | Internal Compose network |
| Celery `worker` | Shared Python task execution | Internal Compose network |
| Celery Beat `scheduler` | Hourly expired-session cleanup | Internal Compose network |
| MinIO `minio` | S3-compatible object storage | Console: http://localhost:9001; API internal |

The API and worker import the same `backend/app` settings and services. Containers bind browser-facing ports to `127.0.0.1`. This is a local development setup; production ingress, TLS and backup/restore deployment follow later milestones.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- Git
- Optional for host-only frontend checks: Node.js 24 and npm

## Quick start

From the repository root, copy the clearly marked **local development** values, then start Compose:

```bash
cp .env.example .env
# In the ignored .env, set TOTP_ENCRYPTION_KEY to a unique Fernet key.
docker compose up --build -d
docker compose ps
docker compose exec -T api alembic upgrade head
docker compose exec api python -m app.auth.cli create-user
docker compose exec -T api python -m app.jobs.smoke
docker compose exec -T api python -m app.core.storage_smoke
```

In PowerShell, use `Copy-Item .env.example .env` for the copy step. Generate a key with `docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, then paste the output into `TOTP_ENCRYPTION_KEY=` in the ignored `.env`. Do this before starting services if you want TOTP; the key never belongs in Git. If you change database credentials, change both `POSTGRES_*` and `DATABASE_URL`. Change MinIO development credentials before non-local use. Production requires HTTPS frontend and public API origins, secure cookies, a TOTP key and TLS to MinIO.

The first health request creates the empty raw bucket automatically. Alembic enables pgvector and creates authentication, raw-ingestion, source, instrument and market-data tables. The source seed enables only authenticated manual CSV uploads. Yahoo is blocked; Stooq, OpenFIGI, SNB and ECB remain unknown and disabled until an explicit operator review. The user command prompts for a username and password without putting the password in shell history. It refuses duplicate usernames. There is no public registration.

Open `http://localhost:3000/login` and sign in. The dashboard and settings routes require a valid server-side session. In **Settings**, adjust timezone/base currency and start two-factor setup: enter the displayed secret in an authenticator app, then confirm its six-digit code. After TOTP is active, login asks for the next code. If the authenticator is lost, a local operator can run `docker compose exec api python -m app.auth.cli reset-totp` (or `make reset-totp`); this revokes all sessions for that user. Preserve `TOTP_ENCRYPTION_KEY` in secure backups.

## URLs

- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard
- Settings: http://localhost:3000/settings
- Instruments and legacy CSV preview: http://localhost:3000/instruments
- Market CSV import: http://localhost:3000/imports
- Data quality: http://localhost:3000/data-quality
- Read-only source status: http://localhost:3000/settings/data-sources
- API readiness: http://localhost:8000/api/v1/health/ready
- API liveness: http://localhost:8000/api/v1/health/live
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

The development MinIO login uses `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` from `.env`.

## Development commands

The `Makefile` offers `make up`, `down`, `build`, `logs`, `test`, `lint`, `format`, `typecheck`, `migrate`, `smoke`, `config`, `create-user`, `reset-totp`, `sources`, `source-review`, `source-enable` and `source-disable`. On Windows without Make, use the equivalent Compose commands:

```bash
docker compose config --quiet
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm run build
```

`docker compose up --build` uses development image targets. The frontend and backend Dockerfiles also provide separate production targets for later deployment. Do not expose the local HTTP setup publicly. Use HTTPS and a controlled ingress before production use.

Backend direct dependencies are declared in `requirements.txt` and `requirements-dev.txt`; the Docker images install the corresponding version-locked `requirements.lock` and `requirements-dev.lock`, including transitive dependencies. Update the lockfiles and rerun the container tests whenever dependency declarations change. The frontend uses `package-lock.json` with `npm ci` in its image.

## Operational behavior

- `/api/v1/health/live` checks the API process. `/api/v1/health` and `/api/v1/health/ready` probe PostgreSQL, Valkey and MinIO and return HTTP 503 with per-service `unavailable` states when a dependency fails.
- The backend assigns or validates `X-Request-ID`, returns it to callers and writes JSON logs with UTC timestamps and request context.
- `system.ping` is a harmless Celery task used by `make smoke`. Celery Beat clears expired/revoked sessions hourly.
- Session cookies are HttpOnly and SameSite=Lax, and Secure in production. Only a SHA-256 hash of the random session token is stored in PostgreSQL. Login rate limits and temporary TOTP challenges use Valkey. No token is stored in browser LocalStorage.
- Auth and settings writes use restricted CORS and Origin checks; security changes are audited. See [authentication architecture](docs/architecture/authentication.md).
- The MinIO wrapper supports bucket initialization, put/get/head and test-only delete. Application raw-ingestion flows retain originals and provenance.
- `RawIngestionService` stores exact bytes with SHA-256 and a durable database reference before preview/parsing. A failed upload is visible as `FAILED`; a database failure after upload leaves a traceable `PENDING` row. Operators reconcile pending rows by checking the object and hash. Application flows do not overwrite or delete raw objects.
- The instrument master uses stable UUIDs and dated ticker/ISIN/FIGI history. Search distinguishes exact matches, name candidates and ambiguous tickers. Manual creation works while external sources are disabled. The legacy CSV preview remains read-only; the P3 import path adds explicit commit for prices, actions and FX.
- OpenFIGI mapping is implemented behind the source gate. It stores the raw response before parsing and requires explicit candidate acceptance. No tests contact live financial data providers; fixtures and `httpx.MockTransport` cover the connector.
- P3 stores current prices, actions and FX separately from append-only versions. The protected import page confirms column mapping and partial rows, then re-verifies immutable raw bytes before commit. Price conflicts require review or quarantine. `as_of` queries use local `known_at` and require a timezone. The instrument page shows canonical closes, source and quality; the data-quality page shows missing, stale and quarantined states.
- FX uses direct, inverse or cross rates for CHF/EUR/USD with a visible, bounded calendar-day carry (`FX_MAX_CARRY_DAYS`, default 5). The ECB daily EXR connector is implemented behind the source gate. The SNB connector remains closed until a daily series and response format are verified. Neither source is enabled by default. Return results are provisional until complete corporate-action coverage can be verified.

## Source administration

Inspect gate status with `docker compose exec -T api python -m app.sources.cli list` or `make sources`. The protected web source page is read-only. An operator can record a documented decision with `python -m app.sources.cli review`, then separately run `enable`; an expired or incomplete review cannot enable or use an external source. `make source-review ARGS="OPENFIGI --status APPROVED ..."` passes review arguments through to the CLI. See [source gate](docs/architecture/source-gate.md) for the required fields and a command example. Do not treat the example as an approval decision.

The protected P2 API exposes instrument create/update/search/detail, source status and the legacy `POST /api/v1/imports/csv/preview`. The P3 API adds `POST /api/v1/market-data/imports/{prices|actions|fx}/preview` and `/commit`, instrument `/prices`, `/prices/{date}/versions`, `/corporate-actions` and `/return`, `GET /api/v1/fx/rate` and `/data-quality/summary`. The CSV request body is UTF-8 `text/csv` with optional `X-Filename` and a 5 MB limit. Confirm the mapping and review row errors before commit; the original raw object is checked again. See [market-data architecture](docs/architecture/market-data.md) for the response and versioning rules.

## Project documents

- [System overview](docs/architecture/system-overview.md)
- [Development environment](docs/architecture/development-environment.md)
- [Authentication architecture](docs/architecture/authentication.md)
- [Raw ingestion](docs/architecture/raw-ingestion.md)
- [Instrument master](docs/architecture/instrument-master.md)
- [Source gate](docs/architecture/source-gate.md)
- [Market data](docs/architecture/market-data.md)
- [Canonical versioning](docs/architecture/canonical-versioning.md)
- [FX data](docs/architecture/fx-data.md)
- [Data quality](docs/architecture/data-quality.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Architecture decisions](docs/decisions/)
- [Repository agent rules](AGENTS.md)

The long-term roadmap is in `MASTER_DEVELOPMENT_PLAN.md`. The next assignment is **normative P4: Portfolio and V1 release**. This local Compose setup is not a production deployment; production ingress, monitoring, backups and restore tests remain later gates.
