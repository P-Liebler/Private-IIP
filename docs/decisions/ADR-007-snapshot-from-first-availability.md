# ADR-007: Snapshot from first availability

**Status:** Accepted as architecture; collectors pending  
**Date:** 2026-10-03

Every future collector must store its original response and provenance before producing canonical records. Data that cannot be reconstructed later starts local snapshotting when its source is first enabled. A historical value imported today is not presented as a value the application observed in the past. This phase prepares MinIO and Alembic; the raw-ingestion table and collector contract arrive with the first source.
