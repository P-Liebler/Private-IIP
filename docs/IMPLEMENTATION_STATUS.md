# Implementation status

**Updated:** 2026-10-12
**Source of truth:** [Master Development Plan](../MASTER_DEVELOPMENT_PLAN.md), section 158.

| Assignment phase | Plan mapping | Status | Delivered |
| --- | --- | --- | --- |
| Phase 0 — project foundation | P0 | DONE | Repository rules, Compose and architecture decisions. |
| Phase 1A — minimal core | P1 subset | DONE | Next.js, FastAPI, settings, PostgreSQL, Alembic and pgvector. |
| Phase 1B — data/background foundation | P1 subset | DONE | Valkey, Celery, MinIO and readiness. |
| Phase 2 — authentication | P1 subset | DONE | Private Argon2id login, sessions, TOTP, settings and audit. |
| P1 raw-ingestion closure | P1 | DONE | Immutable raw objects, hash verification and provenance. |
| Phase 3 — Instrument Master | P2 | DONE | Stable instruments, identifier history, source gate, gated OpenFIGI mapping and CSV preview. |
| Phase 4 — Market Data Foundation | P3 | DONE WITH GATED SOURCES | Manual CSV preview/commit, canonical and versioned prices/actions/FX, validation, reconciliation, quarantine, PIT queries, indicative return, FX derivation, ECB connector, data-quality and UI. SNB daily format remains unverified; its connector fails closed. |
| Portfolio and production access | P4 | FUNCTIONAL — PRODUCTION GATE OPEN | Owned portfolios/accounts, preserved transaction ledger, Decimal WAC, corporate-action application, P3 valuation/FX, returns, snapshots with provenance, transaction CSV, portfolio UI, Caddy/private TLS, monitoring and verified isolated recovery. Target homelab/VPN client trust and an independent production backup mount still require deployment acceptance. |

## P3 contracts and limits

- Manual CSV is the functional input for daily prices, corporate actions and FX. Raw bytes precede parsing; committed values reference their verified raw object. The P2 preview still creates no canonical data. Repeated P3 commit is idempotent.
- Price/action/FX current rows point to append-only versions. `known_at` and explicit timezone-aware `as_of` prevent later corrections from appearing in earlier queries. No historical local availability is inferred from an old event date.
- Hard-invalid rows are rejected and, on explicit partial commit, quarantined. Close disagreement thresholds are 0.25%, 0.50% and 2%; manual override requires a reason. Quality components use 40/25/15/10/10 weights after validation.
- Return arithmetic uses raw close plus explicit validated actions. The API labels results `PROVISIONAL` because P3 cannot attest complete action coverage. Adjusted close is never added to those returns.
- FX supports CHF, EUR and USD, direct/inverse/cross conversion and bounded, visibly dated carry forward (`FX_MAX_CARRY_DAYS`, default 5). No valid rate yields `UNAVAILABLE`.
- Source states: `MANUAL_CSV` APPROVED/enabled; `YAHOO` BLOCKED/disabled; `STOOQ` and `OPENFIGI` UNKNOWN/disabled; `SNB` and `ECB` UNKNOWN/disabled. No live financial provider was activated or called during this phase. The ECB collector has a documented CSV contract behind the gate. The SNB stub remains `SOURCE_FORMAT_UNVERIFIED` after gate approval until a daily series is verified.
- The protected `/imports`, `/data-quality` and instrument pages show import, quality and canonical price states. The legacy instrument CSV preview remains available.

## Verification

- Baseline on `e4c60ba`: 27 backend tests, Ruff, Mypy, frontend typecheck and Compose configuration passed locally. The earlier GitHub Actions run on that commit was reported successful by the user; no remote CI action was initiated for P3.
- After P3: `docker compose exec -T api pytest -q`: **48 passed**, one upstream Starlette warning. Integration tests cover preview/commit, repeat import, correction and `as_of`, quarantine, actions, FX and source gates. No test calls a live provider.
- Existing database upgraded to `0005_p3_contract`; disposable database migration from `0001` through `0005` verified 13 required tables. See `python -m scripts.verify_fresh_migration`.
- `docker compose up -d --build`, `docker compose config --quiet`, Ruff, Mypy, frontend lint/typecheck/build, Alembic schema check, Celery and MinIO smoke checks passed locally. All seven Compose services were healthy and API readiness returned HTTP 200.

## Operational boundary

Local Compose binds public ports to localhost over HTTP. The separate P4 production stack provides HTTPS and Secure cookies, private backend/MinIO access, Prometheus/Grafana and configurable independent backups. Production use still requires acceptance on the actual homelab/VPN hostname and browser trust store, an independent protected backup mount, a daily host schedule and encrypted key recovery. The local tests establish the application and recovery path; they do not establish those external deployment conditions. The P3 source gates are unchanged. See [deployment](architecture/production-deployment.md), [backup/restore](architecture/backup-restore.md) and [P4 acceptance report](P4_ACCEPTANCE_REPORT.md).

## P4 contracts

- Migration `0006_portfolio` adds eight tables: benchmarks, portfolios, portfolio_accounts, transactions, portfolio_action_applications, cash_balances, position_snapshots and portfolio_snapshots. `0007_snapshot_provenance` adds nullable knowledge cutoff and exact input references; existing unknown provenance stays null. No prior migration was changed.
- User ownership is checked on portfolio, account, transaction and derived-report operations. Portfolio-row locks serialize accounting writes and rebuilds. Corrections preserve the old transaction and append a replacement; void timestamps preserve earlier PIT replay.
- WAC includes buy costs; sale fees/taxes reduce proceeds and realized P/L. Negative cash remains visible, oversells fail. Corporate actions apply explicitly and idempotently, block manual double counting and require review for revisions, same-day split/income entitlement and delisting settlement.
- Raw closes and P3 dated FX supply native/base valuations. Missing/stale prices, missing FX and unresolved eligible actions leave the total null and the portfolio `PARTIAL`. Event-date FX provenance supplies realized P/L, income, fees and taxes. Missing historical FX leaves only those analytics unavailable.
- Absolute return, daily-linked TWR, bounded conventional-flow XIRR, annualized TWR CAGR and opening-exposure FX contribution have documented definitions. Portfolio and real-instrument benchmark returns remain `PROVISIONAL` while corporate-action coverage is unverified. Dashboard sums stay in backend Decimal and are grouped by base currency.
- Transaction CSV persists exact raw bytes before preview, supports editable mapping and dated ticker/ISIN/FIGI resolution, and commits atomically. Broker IDs take precedence over normalized fingerprints. Invalid references, ambiguity, duplicates or overselling block commit.
- Portfolio pages provide overview, holdings, performance/value chart, allocation charts, income, transaction entry/correction/void/import and data-quality issues. No P5 or later product feature was introduced.

## P4 verification

Final commands, recovery artifacts, local production evidence and remaining deployment gates are recorded in [P4 acceptance report](P4_ACCEPTANCE_REPORT.md). Remote CI has not been run or reported successful for this work. **V1 NOT READY for an unverified target production deployment.**

The local backend suite now contains 61 passing cases; the two browser cases include explicit dividend-cost confirmation and split application. Manual/canonical effects can be linked after exact review, without double booking. Pre-event quotes and invalid preserved ledger rows cannot become invented valuations. The executable Windows scheduling installer is provided and syntax checked; installation against a real production target remains an operator step.
