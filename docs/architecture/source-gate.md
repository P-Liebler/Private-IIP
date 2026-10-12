# Source rights gate

The `data_sources` seed is deterministic: `MANUAL_CSV` approved and enabled for authenticated user supplied files only; `YAHOO` blocked; `STOOQ`, `OPENFIGI`, `SNB` and `ECB` unknown. All external sources begin disabled. Trust level and priority describe data assessment, not permission. No trust level can override a blocked gate.

Only the server-side CLI changes gate decisions. A review records terms URL, checked time, scope, allowed uses, decision note/reviewer and next review. External approval additionally requires HTTPS terms URL, future review and a positive configured per-minute limit. Review leaves the source disabled; an explicit `enable` checks the full gate again. Expired or disabled approvals fail closed. The read-only `/api/v1/data-sources` endpoint and web page expose status to authenticated users without administrative controls.

`OpenFigiProvider` checks `SourceGate.require_enabled(source, "mapping")` before rate limiting and constructing an HTTP request. The P3 ECB FX collector applies the same gate for `fx_rates` before HTTP; the SNB connector also checks the gate and then fails closed until its daily data format is verified. The shared Valkey limiter uses each source's configured rate and returns a structured 429; if Valkey is unavailable, calls fail closed. Tests use `httpx.MockTransport` and prove that blocked/unknown sources make zero HTTP requests. P3 seeds SNB and ECB as unknown and disabled; Yahoo remains blocked.

Example operator flow after an actual documented rights review:

```bash
docker compose exec -T api python -m app.sources.cli list
docker compose exec -T api python -m app.sources.cli review OPENFIGI --status APPROVED --terms-url https://www.openfigi.com/api/documentation --scope 'approved mapping scope' --use mapping --note 'documented decision' --reviewer operator --next-review 2027-01-01 --rate-limit-per-minute 30
docker compose exec -T api python -m app.sources.cli enable OPENFIGI
```

The example command is syntax only, not a permission decision. The operator must use a real review date, actual terms and a justified limit.
