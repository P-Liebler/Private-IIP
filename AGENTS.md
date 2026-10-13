# Repository rules

Read `MASTER_DEVELOPMENT_PLAN.md` before changing architecture or adding product features. Keep it as the detailed source of truth; update `docs/IMPLEMENTATION_STATUS.md` after each phase.

- Never invent financial data. Missing or stale data must be explicit; do not return `0` or fake production values as a fallback.
- Keep raw financial data immutable. Record provenance for every important value and snapshot non-reconstructable data from its first availability.
- Validate hard constraints before quality scores. Do not let a score rescue invalid data.
- Prevent future information in training and backtests. A signal may only execute at a price tradable after the signal became known.
- Keep production predictions and their outcomes immutable and visible, including bad predictions.
- Quantitative models decide; the LLM only explains. Prefer a simple model when it beats a complex one.
- No autonomous trading, no mandatory paid API/cloud dependency, no fake production fixtures.
- FastAPI and Celery import the same backend settings and domain/service code. Keep concrete providers inside their collector modules.
- Use Alembic for schema changes, UTC internally, stable internal IDs, and no secrets in code, logs or Git.
- Run tests against local services or fixtures; never make live financial provider calls in tests.
- Use Argon2id for passwords. Keep session tokens out of browser storage and plaintext database columns; never log passwords, tokens, TOTP codes or secrets.
- An external provider must pass its approved, enabled, in-scope source gate before any network request. Trust level does not grant usage rights.
- Persist exact provider response bytes and provenance before parsing or canonicalization. Never auto-accept ambiguous identifier mappings.

P1 raw ingestion, P2 identity/source gates and P3 market-data foundation are implemented. P4 is functional with its production gate open. P5 research is functional with gated sources. Keep P6 and later dataset/backtesting, ML, recommendations and assistant features behind their roadmap milestones until requested. P3 returns and P5 Momentum remain restricted until corporate-action coverage is verified. P5 does not close the P4 homelab/VPN, CA, backup-schedule or key-recovery gates.

- Fundamental and estimate versions distinguish public availability from first local observation; historical research requires both <= as_of. Preserve restatements and rejected observations.
- Research scores use versioned deterministic rules and complete required inputs; missing, stale or unresolved conflicting facts suspend affected scores. No private-universe market percentile or investment recommendation is implied.

- The transaction ledger is the accounting source of truth. Portfolio snapshots are derived and reproducible; preserve corrected and voided transactions for audit and point-in-time replay.
- Use Decimal arithmetic with explicit posting precision. Missing or stale prices and FX must never become zero-valued holdings.
- Apply canonical corporate actions explicitly and idempotently; prevent manual/canonical double counting and require review for corrected actions.
