# Private Investment Intelligence Platform

## P10 – lokaler Assistent und Intelligence

`/assistant`, `/documents`, `/alerts`, `/daily-brief`, `/optimizer` und `/time-machine` sind implementiert. Der Assistent erklärt belegte quantitative Ergebnisse mit privaten Read-only-Tools und echten Quellen. Alerts und Daily Briefs funktionieren ohne LLM. Optimizer bleibt Simulation; historische Archive und spätere Rekonstruktion sind getrennt. **V3+ NOT RELEASED**; reale Prognose-, Strategie-, Quellen- und Zielinstallationsgates bleiben offen.

Ollama ist optional: `docker compose --profile llm up -d ollama`, danach Modelle ausdrücklich mit `docker compose exec -T ollama ollama pull qwen3:0.6b` und `docker compose exec -T ollama ollama pull embeddinggemma:300m` laden. Keine Pflicht-API-Kosten; lokale Hardware und Betrieb bleiben notwendig. `DATA_OPERATOR_USERNAMES` ist eine explizite JSON-Allowlist für Dokumentrechte/Kalenderimporte. Quellen beginnen UNKNOWN/deaktiviert und benötigen die getrennte bestehende Source-CLI-Prüfung und Aktivierung; keine Beispiele sind eine Freigabe.

Dokumente brauchen Quellenrechte und einen konkreten SHA-/Speicher-/Indexierungsnachweis. Ohne Inhaltsrechte ist nur freigegebene Metadatenablage möglich. Keine OCR oder automatische Übernahme von PDF-Tabellen als Finanzfakten. Keine Geheimnisse in Chat oder Dokumente eingeben. Chatlöschung/Retention ersetzt keine Backup-Aufbewahrung.

Core-Modellpins bleiben unverändert. Zusätzliche PDF-/Vektor-Pakete werden separat aus `backend/requirements-assistant.lock` mit `--no-deps` installiert; der Modelllader prüft alte numerische Pins unverändert. [ADR-022](docs/decisions/ADR-022-preserve-model-dependency-pins.md).

Nachweise und Grenzen: [P10-Abnahme](docs/P10_ACCEPTANCE_REPORT.md), [Assistent](docs/architecture/local-assistant.md), [RAG](docs/architecture/rag.md), [Sicherheit](docs/architecture/assistant-security.md), [Alerts](docs/architecture/alerts.md), [Daily Brief](docs/architecture/daily-brief.md), [Optimizer](docs/architecture/portfolio-optimizer.md), [Time Machine](docs/architecture/time-machine.md).

## P9 Recommendations — technisch abgenommen, fachlich gesperrt

`/recommendations` bietet versionierte private Investmentprofile, Bestands-/Kandidatenbewertung und unveränderliche Historie. Harte Daten-, Risiko-, Forecast- und Strategie-Gates stehen vor jedem Score. Ohne validierte Produktionsprognosen und reale Strategieabnahme bleibt **NO VALIDATED INVESTMENT RECOMMENDATIONS** sichtbar. Bewertungen und P8-Hypothesen schreiben keine Transaktionen.

Verträge: [Recommendations](docs/architecture/recommendations.md), [Präferenzen](docs/architecture/investment-preferences.md), [Strategie-Backtesting](docs/architecture/recommendation-backtesting.md). **V3 NOT VALIDATED.** [P9-Abnahme](docs/P9_ACCEPTANCE_REPORT.md): 173 Backend-Regressionsfälle plus gezielte Ergänzung, elf Browserfälle und isolierter Restore bestanden. P10 folgt mit eigener technischer Abnahme und unveränderten fachlichen Gates.

## P7 ML — technische Abnahme abgeschlossen

`/models` zeigt Trainingsläufe, versionierte Modellbewertungen und Datenbereitschaft. Die Instrumentseite zeigt Forecast-Status und unveränderliche Prognosehistorie. Fehlende Freigabe bleibt **NO RELIABLE FORECAST**. Synthetische Simulationen sind ausschließlich technische Tests und begründen kein V2-Prognoseprodukt.

Training nutzt gepinnte P6-Datasets, vier getrennte Zeitfenster, sechs lokale CPU-Modelltypen, Platt-Kalibrierung und datenbasierte Conformal-Intervalle. Administration erfordert `ML_OPERATOR_USERNAMES` als explizite JSON-Allowlist. MLflow/Trainingsworker starten nur bei Bedarf mit `docker compose --profile ml up -d --build`. MLflow besitzt keinen Hostport; `MLFLOW_TRACKING_USERNAME` und ein eigenes Secret mit mindestens 24 Zeichen sind erforderlich. Keine Secrets in Git.

Details: [Training](docs/architecture/ml-training.md), [Validierung](docs/architecture/ml-validation.md), [Registry](docs/architecture/model-registry.md), [Freigabegates](docs/architecture/forecast-quality.md). [P7-Abnahme](docs/P7_ACCEPTANCE_REPORT.md) ist abgeschlossen: **MODELS SHADOW / DATA LIMITED**, **V2 NOT VALIDATED**. Die realen Produktions- und Quellen-Gates bleiben offen.

## P8 Risiko, Szenarien und What-if

Die Portfolioansicht bietet **Risiko**, **Korrelationen**, **Szenarien** und **What-if**. „Risiko-Snapshot berechnen“ erzeugt einen unveränderlichen Datenstand aus dem tatsächlichen P4-Ledger und geprüften Kursen/FX/Actions. Volatilität, Beta, Drawdown, VaR/CVaR und Korrelationen benötigen ihre dokumentierten Stichproben und vollständigen Inputs. Fehlende Historie bleibt sichtbar unverfügbar. Exposure und direkte Szenarien können unabhängig davon verfügbar sein.

Szenarien trennen Positions-, FX-, Beta- und Volatilitätshypothesen. What-if kopiert die Bestände, prüft Cash/FX/Quotes/Quantity und zeigt Kosten sowie vorher/nachher. Der reale Ledger bleibt unverändert. Hypothetische historische Risiken verwenden ausdrücklich konstante vorgeschlagene Gewichte; es gibt keine automatische Empfehlung oder Order.

`P8_MAX_INSTRUMENTS=30`, `P8_TIMEOUT_SECONDS=120`; kein MLflow-/ML-Worker-/LLM-Zwang. API-Historien liefern paginierte Zusammenfassungen, Einzelresultate sind user-owned. Formeln: [Risiko](docs/architecture/portfolio-risk.md), [Szenarien](docs/architecture/scenarios.md), [What-if](docs/architecture/what-if.md).

[P8-Abnahme](docs/P8_ACCEPTANCE_REPORT.md): **155 Backend-/10 Browser-Tests**, Head 0014, erfolgreicher isolierter Restore mit Modell-/Forecast-/Risk-/Scenario-/What-if-Historie und exakt CHF 10'180. **P8 FUNCTIONAL — RISK DATA LIMITED; V2.5 NOT RELEASED**. Reale Homelab/VPN-, CA-, Backup- und Schlüssel-Gates bleiben offen. P9/P10 wurden nicht begonnen.

## P6 Point-in-Time und Backtests

Die geschützte Seite `/backtests` erstellt private Universes, importiert Membership-CSV, baut versionierte Datasets und führt tatsächliche Equal-Weight-, Benchmark-, Momentum- und Quality/Value-Baselines aus. Ergebnisse enthalten Equity/Benchmark-Kurven, Kosten, Fills, Herkunft und Datenlücken. `/data-quality` zeigt Dataset-Ausschlüsse und Feature-/Target-Missingness. P7 baut darauf auf.

1. Universe erstellen; Membership mit internen Instrument-UUIDs als CSV hochladen, Vorschau prüfen und bestätigen. Source `MANUAL_PIT` ist standardmäßig UNKNOWN/deaktiviert; ein Operator muss den Scope `universe_membership` ausdrücklich freigeben. Beispielspalten: `instrument_id,valid_from,valid_to,known_at,membership_status`.
2. Historische Availability- und Vollständigkeitsbelege sowie instrumentbezogene Corporate-Action-Coverage über `python -m scripts.review_pit_evidence <review.json>` prüfen. Ein manuell behaupteter Zeitstempel erfüllt keinen strengen Nachweis. [Evidence und Dataset-Vertrag](docs/architecture/pit-datasets.md).
3. Zeitraum, Benchmark-ID, Basiswährung und `STRICT_PIT` oder `RECONSTRUCTED_HISTORICAL` wählen. Ein nachträglicher Import wird nicht zu einem früheren eigenen Archivstand. Im rekonstruierten Modus bleiben methodische Grenzen sichtbar.
4. Dataset auswählen, Baseline, Ausführung und Kosten wählen und starten. Fehlender Open/FX oder ungültige Coverage erzeugt keinen erfundenen Fill. Das Kostenmodell verwendet explizite tägliche Referenz-FX; keine behaupteten historischen Intraday-Spotquotes.
5. Run und Dataset-Qualität prüfen. `POST /api/v1/datasets/{id}/rebuild` prüft gepinnte Inhalte und Raw-Hashes; `POST /api/v1/datasets/{id}/splits` erzeugt sessionbasiertes Purging/Embargo und train-only Referenzwerte. Fehlende historische Versionen werden als Fehler ausgewiesen.

Konfiguration für API und Worker: `P6_MAX_INSTRUMENTS=30`, `P6_MAX_SESSIONS=400`, `P6_MAX_CONCURRENT_RUNS=1`, `P6_TIMEOUT_SECONDS=240`. `CODE_COMMIT` auf den Checkout-Commit setzen; das Manifest speichert zusätzlich den Quelldatei-Hash und Dependency-Lock. API/Worker nach Codeänderungen neu starten, bevor neue wissenschaftliche Runs entstehen. Der Mypy-Cache liegt im Entwicklungscontainer, um Windows-Bind-Mount-Staus zu vermeiden.

P6 ist eine funktionale Grundlage mit historischen Datenbeschränkungen; die technische Simulation beweist keine vollständige reale historische Markt-/Universe-Abdeckung. Siehe [P6-Abnahmebericht](docs/P6_ACCEPTANCE_REPORT.md), [Feature-Formeln](docs/architecture/feature-store.md) und [Backtesting](docs/architecture/backtesting.md). Die realen P4-Produktions-Gates bleiben offen.

## P5 Research

Die geschützten Seiten `/research`, `/watchlists`, `/news` und die Research-Tabs der Instrumentenseite lesen aus eigenen validierten Daten. Fundamentaldaten werden mit Raw-Provenienz und unveränderlichen Versionen importiert; Restatements und historische Wissenszeitpunkte bleiben nachvollziehbar. Bewertungszahlen und Scores benötigen ihre vollständigen geprüften Inputs. Momentum, Forward P/E und PEG bleiben ohne ausreichend belegte Eingaben unverfügbar.

Neue Quellen `SEC_EDGAR`, `COMPANY_IR`, `NEWS_RSS` und `MANUAL_RESEARCH` sind standardmäßig UNKNOWN/deaktiviert. Die bisherige MANUAL_CSV-Freigabe wird nicht erweitert. Ein Operator muss Nutzungsrechte und Scope über die bestehende Source-CLI dokumentieren und die Quelle gesondert aktivieren. `SEC_ENABLED=false` ist eine weitere technische Schranke. Keine Research-Seite fragt live einen Finanzprovider ab.

CSV-Fundamentals: Upload, Spaltenmapping, Vorschau und ausdrückliche Bestätigung auf `/research`. Unterstützte Felder und Zeitverträge stehen in [Fundamentals](docs/architecture/fundamentals.md); Quellenverträge, Bewertungsformeln und Score-Gewichte in den verlinkten P5-Architekturdokumenten. Der [P5-Abnahmebericht](docs/P5_ACCEPTANCE_REPORT.md) dokumentiert die tatsächliche Verifikation und Grenzen.

Die V1-Produktion bleibt wegen der offenen Homelab-/VPN-, CA-, Backup- und Schlüssel-Recovery-Bedingungen nicht freigegeben. P5 erweitert die lokale Research-Funktionalität; die P6-Grundlage steht im vorherigen Abschnitt.

Self-hosted investment research and portfolio platform, built in phases toward the architecture in [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md). P1 raw ingestion, P2 instrument identity/source gates and P3 market-data foundation are implemented. P4 adds portfolio accounting, a V1 UI, monitoring and backup/restore tooling. Check [implementation status](docs/IMPLEMENTATION_STATUS.md) before treating a deployment as production ready. P5 research, P6 PIT/backtesting, P7 guarded local ML and P8 risk/scenarios are implemented with explicit data and deployment limits. Recommendations and the assistant remain later phases.

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
