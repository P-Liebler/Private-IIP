# ADR-007: Snapshot from first availability

**Status:** Implemented for P1/P2 raw ingestion; market collectors pending
**Date:** 2026-10-03
**Updated:** 2026-10-05

Every provider must store its original response and provenance before parsing or producing canonical records. Data that cannot be reconstructed later starts local snapshotting when its source is first enabled. A historical value imported today is not presented as a value the application observed in the past.

P1/P2 adds `raw_ingestions` and `RawIngestionService`. A durable `PENDING` row with a unique object path and SHA-256 is committed before upload. Successful upload advances it to `STORED`; upload failure advances it to `FAILED`. If the final database commit fails, the `PENDING` row retains the object path and hash for operator reconciliation. `get_verified` reads the exact object and refuses hash mismatches. Raw objects are never overwritten or deleted by application flows. See [raw ingestion](../architecture/raw-ingestion.md).
