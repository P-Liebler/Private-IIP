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

P1 raw ingestion, P2 identity/source gates and P3 market-data foundation are implemented. P4 is functional with its production gate open. P5 research is functional with gated sources. P6 provides the dataset/feature/backtesting foundation with explicit historical data limitations. P7 ML is technically functional with SHADOW models and unvalidated real forecasting. P8 risk/scenarios/what-if are functional with explicit data limits; V2.5 target deployment is not released. P9 recommendations are technically functional with hard forecast/strategy gates; no real V3 recommendations are validated. P10 provides the local evidence-only assistant, private RAG, versioned alerts/briefs, simulation optimizer and strict/reconstructed archive inspection after separate P9 acceptance. V3+ target deployment remains unreleased. P3 returns and P5 Momentum remain restricted until corporate-action coverage is verified. P5/P6 do not close the P4 homelab/VPN, CA, backup-schedule or key-recovery gates.

- Fundamental and estimate versions distinguish public availability from first local observation; historical research requires both <= as_of. Preserve restatements and rejected observations.
- Research scores use versioned deterministic rules and complete required inputs; missing, stale or unresolved conflicting facts suspend affected scores. No private-universe market percentile or investment recommendation is implied.

- The transaction ledger is the accounting source of truth. Portfolio snapshots are derived and reproducible; preserve corrected and voided transactions for audit and point-in-time replay.
- Use Decimal arithmetic with explicit posting precision. Missing or stale prices and FX must never become zero-valued holdings.
- Apply canonical corporate actions explicitly and idempotently; prevent manual/canonical double counting and require review for corrected actions.

- Never use future data in features; labels are unavailable until their evaluation window ends and all required inputs are observed.
- Never fill an order at a price already used to generate its signal. FX used for a fill must pass the execution-time availability contract.
- Dataset and backtest versions pin data content, raw/canonical IDs, rules, calendars, code and configuration. Replays never substitute current data.
- Unverified historical membership is not PIT-safe. Reconstructed history and synthetic simulations must be labeled explicitly.
- Availability reviews have their own knowledge date and never silently upgrade old observations. Action coverage is instrument- and interval-specific.
- Restart API/worker processes after code changes before scientific runs; the code manifest is fixed for the running process. Do not run browser dataset builds concurrently with backend integration tests against the same limited local services.

- ML promotion uses fixed versioned gates plus an authorized operator review. Synthetic/reconstructed evidence cannot establish a production forecast. Calibration and final test stay separate; degraded models cannot auto-return to production.
- Risk returns use the real ledger, daily external-flow neutralization and explicit closed-session alignment. Missing open-day prices, FX or corporate-action coverage suspend affected metrics.
- Risk/scenario/what-if snapshots are immutable; corrections create new records. What-if never mutates the transaction ledger, and pro-forma histories must be labeled. Preserve scenario calculation types and include negative cash in FX translation exactly once.

- Investment profiles, recommendation rules/results, strategy backtests and reviews are append-only. Hard gates precede scoring; synthetic or shadow evidence cannot authorize real recommendations. Pin profile/model/risk/research/code inputs and preserve abstentions.
- Recommendation simulations reuse P8 and P6; never write the ledger. Replay archived forecasts and constraints only, never today's ranking in the past.


- Assistant tools are a typed read-only allowlist. Models may select existing evidence IDs and fixed explanations only; they cannot create financial claims, citations, permissions or orders.
- Documents require source-use gates and explicit document rights. Store exact originals before parsing; preserve chunks, hashes and embedding model versions. Historical retrieval requires actual local creation/observation before the cutoff.
- Keep numerical model pins in requirements.lock unchanged unless intentionally migrating the model runtime. Install supporting document/vector pins from requirements-assistant.lock with --no-deps and pip check; never weaken model artifact dependency checks or rewrite archived model manifests.
- Alerts and briefs must work without an LLM, distinguish unavailable from false/zero, and persist restart-safe deduplication. Optimizer runs never change the ledger. Time Machine never backdates a model or prediction.
- Run browser acceptance against a completed standalone build using ops/docker-compose.e2e.yml; stop the development server before building its shared output. Reset ASSISTANT_TEST_MODE after controlled tests.

- PR1 collector requests recheck source rights on every attempt, pin public DNS connections and archive exact bounded response bytes before parsing. Recurring collection defaults off; technical provider support never grants usage rights.
- Preserve versioned P6 row-hash contracts across schema additions. Legacy hashes may exclude only known migration-default additions; never rewrite old manifests or weaken model dependency gates.
- Monthly SNB macro/reference observations never substitute daily portfolio FX. Coverage and source failures remain explicit; PR1 does not authorize PR2 model/strategy validation or promotion.

- PR2 validation reuses PR1/P6/P7/P9 and appends evidence records. Source approval, real-data readiness, technical success and financial validation are separate states. Never relabel synthetic originals as real or reconstructed data as locally archived history.
- Pre-register untouched OOS windows, parameters, costs and code before PR2 evaluation. Do not retune from final test results or reuse reserved windows. Forward SHADOW begins at actual generation time, remains experimental and cannot authorize P9 recommendations.
- Forward scheduling defaults off and requires explicit global and policy opt-in. Restore verification includes validation records and existing source/collector checkpoints. PR2 does not close final homelab production gates.

- PR4 security evidence binds exact image/config digests, scanner and database versions, original SBOM bytes and source/lock/report hashes. A changed build needs its own scan; missing or failed scans are SCAN_INCOMPLETE, never a zero-finding success.
- Production deployment requires separate documented security, target-host and operator approval of an immutable manifest and starts only its digest-pinned images with --no-build. Local RC evidence cannot authorize production. Unreviewed Critical findings remain blockers; source, model and strategy gates are independent.

- PR6 UI capabilities are visibility hints only; backend source/operator/ownership gates remain authoritative. Theme preference cookies contain no credentials or financial drafts.
- UI retry receipts and document removals are append-only technical records, separate from financial observations. Commit resource and receipt atomically; a changed payload cannot reuse a completed request key. Retrying a voided booking never resurrects it.
- Document removal withdraws content from the active library and new retrievals, including historical searches; immutable originals and previous evidence remain retained and the UI must say so. Never rewrite old Intelligence hashes to include a newly introduced table; new receipt/removal hashes are separate restore checks.
- Risk chart displays derive only from pinned P8 observations using versioned Decimal rules. Incomplete returns suspend the curves; a missing benchmark is not a zero-return benchmark. Never alter a stored risk snapshot to add display fields.
- Keep MLflow a private authenticated tracking/artifact service. Application training runs in Celery; MLflow server jobs and custom scorer execution remain disabled unless separately reviewed. Never migrate the object store or PostgreSQL major as an automatic security fallback.

- OpenShift/GitOps uses a separate target deployment contract. Compose RC evidence, Argo sync status and local arbitrary-UID tests never authorize cluster deployment or source/model promotion.
- Keep OpenShift compatible with namespace-assigned UIDs/groups and restricted SCCs. No anyuid/privileged fallback, root storage init, automatic PVC pruning or implicit migration hooks. Reuse existing backup artifact/hash contracts with explicit transport, writer quiescence and a held cluster lock.
