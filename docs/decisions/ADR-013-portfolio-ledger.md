# ADR-013: Portfolio ledger and corrections

**Status:** Accepted for P4, 2026-10-12.

V1 uses an account-scoped weighted average cost ledger. Financial posting uses `Decimal` with half-even, eight-decimal cash/basis precision. A sell larger than the account position is rejected; negative cash is allowed. Transactions are preserved. Corrections append a replacement and void the prior row with a UTC timestamp; point-in-time replay can still see the prior state. Audit events record creates, updates and voids.

Canonical corporate actions never silently rewrite user transactions. A unique application record creates at most one system effect per account/instrument/action date/type. Manual same-date effects and corrected canonical versions require review. Derived snapshots may be rebuilt and are keyed by an input hash; they are never the source of truth. This keeps V1 accounting understandable without an event-sourcing framework.

New snapshots persist their UTC knowledge cutoff and exact dependency references, including historical event FX. Migration 0007 leaves missing provenance on older snapshots null rather than inferring a historical availability claim. Portfolio-row locks serialize rebuilds and ledger writes.
