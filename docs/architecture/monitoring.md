# Monitoring (P4)

The internal-only `/internal/metrics` endpoint exposes HTTP request totals, duration sums, error statuses, DB readiness, failed raw ingestions, quarantined rows, stale instruments, valuation failures and backup status. Caddy blocks this path from the public/VPN site; Prometheus scrapes it on the private Compose network. Route labels are templated paths, avoiding per-user and UUID cardinality. The endpoint contains no credentials or portfolio amounts. Metrics reset on an API process restart; historical series live in Prometheus.

`ops/prometheus/alerts.yml` contains rules for API/DB outage, repeated import failure, stale prices and missing/failed/old backups. Operators inspect firing rules in local Prometheus or Grafana; no paid SMS integration is required. Grafana's Prometheus data source and V1 health dashboard are provisioned from version-controlled files. Both UIs bind localhost for SSH/VPN access. Structured JSON application logs retain request IDs; Loki is deferred.

Operational status is also exposed to authenticated users through `/api/v1/system/backup-status` and the Data Quality page. It shows last backup and isolated restore success/date when files exist, otherwise `UNAVAILABLE`. Production use requires checking that alerts are delivered to the operator's actual monitoring workflow.

Valkey connectivity and Celery queue depth are exposed as gauges. Worker/scheduler process health is checked by Compose (targeted Celery ping and scheduler PID); queue depth alone does not prove that a worker is consuming jobs. The latency panel divides the duration-sum rate by the request-count rate.

## P7/P8

ML exposes persisted training/failure totals, prediction abstentions/inference failures, latest review status counts and observed calibration drift. Missing outcomes expose unavailable drift (NaN), never invented zero drift. Risk exposes process-local calculation failure counters, persisted snapshot/partial/VaR-unavailable totals and scenario/what-if totals. Labels contain no user, portfolio, instrument, dataset or prediction IDs. Persisted totals include explicitly labeled local acceptance fixtures.

Prometheus alerts cover repeated risk failures, ML training failure and observed calibration drift; Grafana adds corresponding health panels. Partial financial data is a data-quality state, not an HTTP/server failure. Successful target delivery and alert handling remain deployment acceptance gates.
