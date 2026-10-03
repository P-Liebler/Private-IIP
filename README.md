# Private Investment Intelligence Platform

Self-hosted investment research and portfolio platform, built in phases toward the architecture in [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md). This repository now includes **Phase 2: private authentication and core settings**. Financial collectors, portfolio accounting and forecasts are not yet implemented.

## Current architecture

| Service | Purpose | Local address |
| --- | --- | --- |
| Next.js `web` | Login, protected dashboard and settings | http://localhost:3000 |
| FastAPI `api` | Health, authentication and settings API | http://localhost:8000 |
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

In PowerShell, use `Copy-Item .env.example .env` for the copy step. Generate a key with `docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, then paste the output into `TOTP_ENCRYPTION_KEY=` in the ignored `.env`. Do this before starting services if you want TOTP; the key never belongs in Git. If you change database credentials, change both `POSTGRES_*` and `DATABASE_URL`. Change MinIO development credentials before non-local use. Production requires HTTPS frontend, secure cookies, a TOTP key and TLS to MinIO.

The first health request creates the empty raw bucket automatically. Alembic enables pgvector and creates `users`, `sessions` and `audit_events`. The user command prompts for a username and password without putting the password in shell history. It refuses duplicate usernames. There is no public registration.

Open `http://localhost:3000/login` and sign in. The dashboard and settings routes require a valid server-side session. In **Settings**, adjust timezone/base currency and start two-factor setup: enter the displayed secret in an authenticator app, then confirm its six-digit code. After TOTP is active, login asks for the next code. If the authenticator is lost, a local operator can run `docker compose exec api python -m app.auth.cli reset-totp` (or `make reset-totp`); this revokes all sessions for that user. Preserve `TOTP_ENCRYPTION_KEY` in secure backups.

## URLs

- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard
- Settings: http://localhost:3000/settings
- API readiness: http://localhost:8000/api/v1/health/ready
- API liveness: http://localhost:8000/api/v1/health/live
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

The development MinIO login uses `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` from `.env`.

## Development commands

The `Makefile` offers `make up`, `down`, `build`, `logs`, `test`, `lint`, `format`, `typecheck`, `migrate`, `smoke`, `config`, `create-user` and `reset-totp`. On Windows without Make, use the equivalent Compose commands:

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
- The MinIO wrapper supports bucket initialization, put/get/head and test-only delete. Future raw-ingestion code must retain originals and their provenance.
- No tests contact live financial data providers. Future connectors will use stored fixtures and source-rights gates.

## Project documents

- [System overview](docs/architecture/system-overview.md)
- [Development environment](docs/architecture/development-environment.md)
- [Authentication architecture](docs/architecture/authentication.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Architecture decisions](docs/decisions/)
- [Repository agent rules](AGENTS.md)

The long-term roadmap is in `MASTER_DEVELOPMENT_PLAN.md`. The next development assignment is **Phase 3: Instrument Master**, followed by **Phase 4: Market Data Foundation**.
