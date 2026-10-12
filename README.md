# Private Investment Intelligence Platform

Self-hosted investment research and portfolio platform, built in phases toward the architecture in [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md). P1 raw ingestion, P2 instrument identity/source gates and P3 market-data foundation are implemented. P4 adds portfolio accounting, a V1 UI, monitoring and backup/restore tooling. Check [implementation status](docs/IMPLEMENTATION_STATUS.md) before treating a deployment as production ready. Fundamentals, ML, recommendations and the assistant remain later phases.

## Current architecture

| Service | Purpose | Local address |
| --- | --- | --- |
| Next.js `web` | Login, dashboard, portfolios, instruments, CSV import, data quality and settings | http://localhost:3000 |
| FastAPI `api` | Authentication, market data and portfolio API | http://localhost:8000 |
| PostgreSQL + pgvector `postgres` | Alembic-managed database | Internal Compose network |
| Valkey `valkey` | Celery broker and result backend | Internal Compose network |
| Celery `worker` | Shared Python task execution | Internal Compose network |
| Celery Beat `scheduler` | Hourly expired-session cleanup | Internal Compose network |
| MinIO `minio` | S3-compatible object storage | Console: http://localhost:9001; API internal |

The API and worker import the same `backend/app` settings and services. Development containers bind browser-facing ports to `127.0.0.1`. The separate production Compose file adds Caddy, Prometheus and Grafana behind a private ingress boundary.

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

The first health request creates the empty raw bucket automatically. Alembic enables pgvector and creates authentication, raw-ingestion, market-data and portfolio tables. The source seed enables only authenticated manual CSV uploads. Yahoo is blocked; Stooq, OpenFIGI, SNB and ECB remain unknown and disabled until an explicit operator review. The user command prompts for a username and password without putting the password in shell history. It refuses duplicate usernames. There is no public registration.

Open `http://localhost:3000/login` and sign in. The dashboard and settings routes require a valid server-side session. In **Settings**, adjust timezone/base currency and start two-factor setup: enter the displayed secret in an authenticator app, then confirm its six-digit code. After TOTP is active, login asks for the next code. If the authenticator is lost, a local operator can run `docker compose exec api python -m app.auth.cli reset-totp` (or `make reset-totp`); this revokes all sessions for that user. Preserve `TOTP_ENCRYPTION_KEY` in secure backups.

## URLs

- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard
- Portfolios: http://localhost:3000/portfolios
- Settings: http://localhost:3000/settings
- Instruments and legacy CSV preview: http://localhost:3000/instruments
- Market CSV import: http://localhost:3000/imports
- Data quality: http://localhost:3000/data-quality
- Read-only source status: http://localhost:3000/settings/data-sources
- API readiness: http://localhost:8000/api/v1/health/ready
- API liveness: http://localhost:8000/api/v1/health/live
- API docs: http://localhost:8000/docs
- Internal metrics on localhost development API: http://localhost:8000/internal/metrics
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

`docker compose up --build` uses development image targets. Do not expose the local HTTP setup publicly. The production target uses the separate Compose file below.

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

## Portfolio quickstart

1. Sign in and open [Portfolios](http://localhost:3000/portfolios). Create a portfolio with CHF, EUR or USD as its base currency.
2. Open it, create a Broker, Cash or Manual account, then record a `DEPOSIT`.
3. Create or find an instrument on the Instrument page. Record a `BUY` with the matching instrument and native currency. Record further trades, dividends and fees in the transaction tab. Corrections keep the old booking as voided history.
4. Import validated prices and FX from the Market CSV page. Portfolio valuation shows native values and a full base-currency total only when all required prices/FX and corporate actions are usable. Missing or stale inputs show `PARTIAL` and issues.
5. Open Positions, Performance, Allocation, Dividends and Data Quality in the portfolio. For transaction CSV, choose an account, upload UTF-8 columns `type,trade_date,instrument_id,quantity,price,amount,currency,fee,tax`, review every row, then commit. Duplicate or invalid rows block the whole import.

The protected API includes `/api/v1/portfolios`, account and transaction routes, valuation, holdings, allocation, performance, benchmark and snapshot routes. See [portfolio accounting](docs/architecture/portfolio-accounting.md) and [performance](docs/architecture/portfolio-performance.md) for the formulas and availability rules.

The CSV mapping accepts ticker/ISIN/FIGI or internal instrument ID, trade/settlement dates, the selected account, fees, taxes, notes and broker IDs. Unknown headers open the mapping form before validation. Dashboard totals are grouped by base currency. Daily, lifetime and YTD absolute returns and benchmark comparisons remain visibly provisional until corporate-action coverage is attested.

Browser acceptance uses Playwright against an explicit disposable local test user. Run `npx playwright install chromium`, set `E2E_USERNAME`, `E2E_PASSWORD`, `E2E_PORTFOLIO_ID` to a fixture created with `scripts.create_restore_fixture`, then `npm run test:e2e` in `frontend/web`. The tests inspect that fixture and create/archive a separate browser portfolio, including a missing-price scenario. Run fixture creation only in a disposable acceptance instance. Browser artifacts are ignored by Git and Docker. Development startup synchronizes the node_modules volume when the package lock changes.

## Production and recovery

Copy `ops/production.env.example` to a secure location outside Git, replace every placeholder and set `BACKUP_ROOT` to an independent protected disk or NAS mount. Bind Caddy to localhost or a VPN interface. The production file keeps API, database and MinIO off host ports; Grafana and Prometheus bind localhost.

```text
docker compose -f docker-compose.prod.yml --env-file /secure/production.env config --quiet
docker compose -f docker-compose.prod.yml --env-file /secure/production.env up -d --build
docker compose -f docker-compose.prod.yml --env-file /secure/production.env exec -T api alembic upgrade head
python ops/backup.py --compose-file docker-compose.prod.yml --env-file /secure/production.env --root /separate/private-iip --prune
```

Schedule the backup command daily on the host. Protect configuration and the Fernet TOTP key in a separate encrypted backup. Periodically run `ops/restore_verify.py` against an explicit disposable fixture; it verifies hashes, migration head, login and an exact valuation in isolated PostgreSQL and MinIO. See [deployment](docs/architecture/production-deployment.md), [backup/restore](docs/architecture/backup-restore.md) and [monitoring](docs/architecture/monitoring.md). A localhost TLS smoke test does not establish trust on a real VPN client or domain.

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
- [Portfolio accounting](docs/architecture/portfolio-accounting.md)
- [Portfolio performance](docs/architecture/portfolio-performance.md)
- [Production deployment](docs/architecture/production-deployment.md)
- [Backup and restore](docs/architecture/backup-restore.md)
- [Monitoring](docs/architecture/monitoring.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Architecture decisions](docs/decisions/)
- [Repository agent rules](AGENTS.md)

The long-term roadmap is in `MASTER_DEVELOPMENT_PLAN.md`. P5 fundamentals and research begins only after a separate assignment. Production readiness requires the P4 gates and operator verification documented in the implementation status.
