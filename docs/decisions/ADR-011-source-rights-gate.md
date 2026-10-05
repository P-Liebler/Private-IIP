# ADR-011: Source rights are separate from trust

**Status:** Accepted
**Date:** 2026-10-05

## Decision

The `data_sources` registry records technical trust and source permission independently. External providers start `UNKNOWN` and disabled unless a specific review has recorded terms URL, scope, allowed uses, reviewer, checked date, future review date and rate limit. `SourceGate.require_enabled` runs before HTTP. Approval does not itself enable a source; the operator enables it separately. Expired approvals fail closed. A Valkey limit coordinates provider calls across workers.

The bootstrap marks Yahoo `BLOCKED`, Stooq and OpenFIGI `UNKNOWN`, and user supplied CSV `APPROVED` solely for `manual_upload`. No external source is queried by bootstrap or tests. See [source gate](../architecture/source-gate.md).
