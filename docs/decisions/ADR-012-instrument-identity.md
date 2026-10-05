# ADR-012: Instrument UUID and identifier history

**Status:** Accepted
**Date:** 2026-10-05

## Decision

An instrument has a stable internal UUID. Ticker, ISIN and FIGI are normalized and stored with validity dates, observation time and optional source/raw provenance in `instrument_identifiers`. Current values on `instruments` are convenience fields maintained by `InstrumentService` in the same transaction. The service rejects overlapping assignments and the database prevents duplicate current assignments for the same identifier and market key. Search reports exact versus name candidate matches and ambiguity; no search or OpenFIGI result merges records automatically.

For a ticker, market key is MIC or exchange; ISIN and FIGI are global. Existing instrument identity survives ticker changes and historical lookups. See [instrument master](../architecture/instrument-master.md).
