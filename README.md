# Private Investment Intelligence Platform

Self-hosted investment research and portfolio platform, built in phases toward the architecture in [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md). This repository currently contains the **development foundation only**: no financial collectors, portfolio accounting, forecasts or authentication.

## Current architecture

| Service | Purpose | Local address |
| --- | --- | --- |
| Next.js `web` | Development status page | http://localhost:3000 |
| FastAPI `api` | Health API and future application entry point | http://localhost:8000 |
| PostgreSQL + pgvector `postgres` | Alembic-managed database | Internal Compose network |
| Valkey `valkey` | Celery broker and result backend | Internal Compose network |
| Celery `worker` | Shared Python task execution | Internal Compose network |
| Celery Beat `scheduler` | Scheduler, currently without financial jobs | Internal Compose network |
| MinIO `minio` | S3-compatible object storage | Console: http://localhost:9001; API internal |

The API and worker import the same `backend/app` settings and services. The UI reads `/api/v1/health/ready` and reports missing services as unavailable. Containers bind their browser-facing ports to `127.0.0.1`; no public access or production authentication is configured yet.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- Git
- Optional for host-only frontend checks: Node.js 24 and npm

## Quick start

From the repository root, copy the clearly marked **local development** values, then start Compose:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec -T api alembic upgrade head
docker compose exec -T api python -m app.jobs.smoke
docker compose exec -T api python -m app.core.storage_smoke
```

In PowerShell, use `Copy-Item .env.example .env` for the copy step. The root `.env` is ignored by Git. If you change the database username or password, change both `POSTGRES_*` and `DATABASE_URL` consistently. Change MinIO development credentials before using any non-local environment. Production requires TLS to MinIO and deliberately rejects development credentials.

The first health request creates the empty raw bucket automatically. No manual container preparation or data seeding is required. The Alembic migration enables pgvector; domain tables will be added in later phases.

## URLs

- Frontend: http://localhost:3000
- API readiness: http://localhost:8000/api/v1/health/ready
- API liveness: http://localhost:8000/api/v1/health/live
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

The development MinIO login uses `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` from `.env`.

## Development commands

The `Makefile` offers `make up`, `down`, `build`, `logs`, `test`, `lint`, `format`, `typecheck`, `migrate`, `smoke` and `config`. On Windows without Make, use the equivalent Compose commands:

```bash
docker compose config --quiet
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm run build
```

`docker compose up --build` uses development image targets. The frontend and backend Dockerfiles also provide separate production targets for the later production deployment phase. Do not expose this unauthenticated foundation outside localhost/LAN before the access-control phase.

Backend direct dependencies are declared in `requirements.txt` and `requirements-dev.txt`; the Docker images install the corresponding version-locked `requirements.lock` and `requirements-dev.lock`, including transitive dependencies. Update the lockfiles and rerun the container tests whenever dependency declarations change. The frontend uses `package-lock.json` with `npm ci` in its image.

## Operational behavior

- `/api/v1/health/live` checks the API process. `/api/v1/health` and `/api/v1/health/ready` probe PostgreSQL, Valkey and MinIO and return HTTP 503 with per-service `unavailable` states when a dependency fails.
- The backend assigns or validates `X-Request-ID`, returns it to callers and writes JSON logs with UTC timestamps and request context.
- `system.ping` is a harmless Celery task used by `make smoke`. Celery Beat starts with an empty schedule.
- The MinIO wrapper supports bucket initialization, put/get/head and test-only delete. Future raw-ingestion code must retain originals and their provenance.
- No tests contact live financial data providers. Future connectors will use stored fixtures and source-rights gates.

## Project documents

- [System overview](docs/architecture/system-overview.md)
- [Development environment](docs/architecture/development-environment.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Architecture decisions](docs/decisions/)
- [Repository agent rules](AGENTS.md)

The long-term roadmap is in `MASTER_DEVELOPMENT_PLAN.md`. The next development assignment after this foundation is **Authentication + Core**; it is intentionally outside the current implementation.
