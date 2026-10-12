# ADR-003: Point-in-time data contracts

**Status:** Accepted; P3 price, action and FX versioning implemented
**Date:** 2026-10-03

Future financial records distinguish event time, public `known_at`, and local `retrieved_at`/`observed_at`. Corrections append a new version and retain the prior raw and canonical versions. Historical queries may only use versions demonstrably available at the queried instant. This foundation creates the storage and migration boundaries, not historical financial records.
