# Backup and restore (P4)

PR3 extends these tools with a shared host OS lock across backup/restore/retention, artifact size, a separate last-success status and visible integrity rejection before restore commands. See [backup setup](../operations/BACKUP_SETUP.md), [secret recovery](../operations/SECRET_MANAGEMENT.md) and [disaster recovery](../operations/DISASTER_RECOVERY.md). Linux timer/service files are operator-installed templates; no real schedule or independent destination has been verified.

`ops/backup.py` writes a PostgreSQL custom-format dump and mirrors the immutable MinIO raw bucket to a unique backup set. The manifest records UTC start/end, duration, DB name, success state, file names and SHA-256 of every artifact. `BACKUP_ROOT` is configurable and should be an independent protected mount for production. The script writes its last status to `runtime/backup-status.json`; the authenticated Data Quality page shows it. Schedule the script daily on the host (systemd timer or Windows Task Scheduler). `--prune` keeps the newest seven daily, four weekly and six monthly successful sets. Deletion is confined to direct children of the resolved `BACKUP_ROOT/sets` directory. Keep config and secrets, particularly `TOTP_ENCRYPTION_KEY`, in a separate encrypted backup; they are intentionally absent from application artifacts.

Example, after setting `BACKUP_ROOT` and using the secure production env file:

```text
python ops/backup.py --compose-file docker-compose.prod.yml --env-file /secure/production.env --root /separate/private-iip --prune
```

`ops/restore_verify.py` first verifies all manifest checksums. It then starts a randomly named, isolated Compose project with a new PostgreSQL instance, a new MinIO instance and no exposed host ports. It restores the dump, mirrors raw objects into the separate MinIO, starts the API, and runs `scripts.verify_restored_fixture`. That verifier checks Alembic head, user/accounting rows, exact raw-object hash, login and an expected complete portfolio value. The isolated project is removed with volumes afterward; `runtime/restore-status.json` records success or failure. Use an explicit disposable fixture and pass its test password via `RESTORE_TEST_PASSWORD`; never use a real user's password.

The local P4 acceptance fixture uses CHF 10,000 deposit, 10 USD shares bought at 100, accepted raw close 120 and USD/CHF 0.9. Its expected complete value is CHF 10,180. The backup/restore test must compare that exact value and raw SHA after restore. Repeat the restore test periodically and after backup process changes. A successful dump command alone is not a restore gate.

An empty raw bucket is a valid backup state: the successful mirror and an empty `raw/` directory are recorded with `raw_object_count=0`; no fake object is created. Runtime status omits the potentially large checksum map, which stays in the backup manifest. Caddy's private CA material and the TOTP key belong in the separate encrypted secrets backup; recreating the CA requires updating client trust. Application backup artifacts never include the production env file.

On Windows, register the daily host job with `ops/install_backup_schedule.ps1 -EnvFile C:\secure\production.env -BackupRoot E:\private-iip-backup`; add `-WhatIf` to inspect registration first. It runs at 03:00, starts missed jobs when available, prevents overlapping runs and applies retention. It never overwrites an existing task or stores passwords in the task arguments. Registration needs the host's Task Scheduler rights. The default S4U identity uses local resources; an NAS/UNC target requires an operator-configured identity with appropriate network access. Run and inspect the real scheduled task once before accepting production scheduling. No schedule is installed by application startup or a local acceptance test.

## P7/P8

The PostgreSQL dump includes ML registry/jobs/reviews, immutable predictions and corrected outcomes, risk snapshots, seeded scenario definitions, scenario runs and what-if runs. Optional MLflow metadata/auth schemas live in the same database and are included. The immutable raw bucket also contains internally hashed data-only model artifacts and MLflow artifact copies. No separate untracked model directory is required.

`--model-id` plus `--expected-artifact-hash` verifies the internal model bytes, associated pinned dataset, MLflow run metadata and tracked artifact copy. `--prediction-history-hash` verifies exact immutable prediction/outcome history. `--risk-history-hash` verifies exact risk/scenario/what-if records, parent/content hashes, pinned canonical payloads and raw response SHA-256. Generate checkpoints with `scripts.p7_restore_checkpoint <model_uuid>` and `scripts.p8_restore_checkpoint <portfolio_uuid>` before creating the backup. Use an explicit disposable fixture account via the existing restore-password environment contract.

A successful local isolated restore includes the exact CHF 10'180 ledger valuation. It does not establish an independent production backup mount, actual host schedule or recovery of private CA/TOTP secrets. Those production gates remain open.

## P9

PostgreSQL includes immutable investment-profile versions, recommendation rules, strategy backtests/reviews and every recommendation including abstentions. `scripts.p9_restore_checkpoint <portfolio_uuid>` calculates the owned history hash and verifies exact recommendation replay. Pass it as `--recommendation-history-hash` to the isolated restore verifier. It compares complete profile/rule/review/backtest/recommendation contents, not merely row counts. Continue verifying the P7/P8 histories, pinned raw bytes and exact P4 value alongside it.


## P10: private intelligence recovery

Migration 0016 adds private chats/tool-call evidence, document rights/metadata/chunks/pgvector embeddings, alert versions/evaluations/events, notifications, daily-brief configuration/history, optimizer runs and calendar-event versions. PostgreSQL backups contain exact vectors and their model versions; MinIO backups contain byte-identical original PDFs and calendar JSON. `python -m scripts.p10_checkpoint PORTFOLIO_UUID` verifies raw/chunk hashes and computes `intelligence_history_hash` over all owned P10 metadata and exact stored vectors. Pass it to `ops/restore_verify.py --intelligence-history-hash HASH` together with the existing P6/P7/P8/P9 checks. The isolated verifier requires restored documents, embeddings, alert evaluations and briefs; it never downloads an LLM.

Ollama weights are optional reproducible runtime assets in `ollama_data`; they are outside the financial-data backup. Re-pull and verify the recorded full digest before using existing embeddings. A different embedding version requires an explicit additive reindex, never silent vector replacement. Source rights remain gates after recovery. Chat deletion/retention changes the active database; existing backup retention remains a separate operator obligation. Freeze background dispatch and user writes when capturing a cross-service acceptance checkpoint; resume them after the backup.
