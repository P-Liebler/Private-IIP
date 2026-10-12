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

P1 raw ingestion, P2 instrument identity/source gates and P3 market-data foundation are implemented. Keep P4 portfolio, ML, recommendations and assistant features behind their roadmap milestones until requested. P3 return results remain provisional until corporate-action coverage can be verified.
