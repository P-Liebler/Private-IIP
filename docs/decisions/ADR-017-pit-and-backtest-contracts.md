# ADR-017: P6 historical evidence, immutable datasets and execution

Accepted 2026-10-13, Masterplan 75–95/158.

1. Separate STRICT_PIT from RECONSTRUCTED_HISTORICAL. Manual assertion text is not verified publication evidence; append-only operator reviews have their own knowledge date.
2. Owned universes distinguish effective membership from knowledge. Completeness including delistings needs interval evidence. Today's directory is not a historical universe.
3. Use offline pinned exchange-calendars and versioned session horizons. No invented holiday lists.
4. Central immutable feature snapshots pin canonical versions. Immutable JSONB dataset/run aggregates retain manifests, labels, orders, fills and quality without creating a separate ML service.
5. Labels have separate future realization/availability intervals. Purge actual overlap and apply conservative session embargo before validation and test. Train-only baselines cannot read validation/test labels.
6. Default next-session open; never fill a signal at its own information close. Explicit costs, FX and action entitlements precede model comparisons.
7. Research identity v2 excludes incidental live-refresh as_of but includes semantic outputs, exact input versions and rules. Explicit historical cutoffs remain part of identity; unchanged live results reuse the first immutable observation. Age/eligibility changes create a new result. Old snapshots are preserved.
8. Resolve the CI EACCES by installing the browser runner in a runner-owned temporary directory. Do not change global ownership or permissions.

P4 production gates and external source activation are independent. P7 training, predictions and Forecast UI are outside P6.
