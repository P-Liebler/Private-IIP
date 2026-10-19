# Production deployment (P4)

PR3 adds [deployment/configuration/network/CA/secret runbooks](../operations/DEPLOYMENT_GUIDE.md), `ops/preflight.py`, a default-dry-run deployment wrapper and a protected operator status view. Staging now uses the same secure settings as production with a separate project and secrets. Caddy is pinned to the reviewed 2.11.7 image digest; remaining image findings prevent a security release. See the [PR3A review](../PR3A_DEPLOYMENT_SECURITY_REPORT.md). Actual host/client acceptance remains unverified.

`docker-compose.prod.yml` is separate from the localhost development stack. Caddy serves the web UI and `/api/v1/*` over HTTPS, blocks `/internal/*`, and gives the API a private HTTPS path to MinIO. The MinIO TLS connection validates Caddy's persisted internal CA; the API, worker and scheduler share this trust root. Only Caddy's 80/443 ports bind `VPN_BIND_ADDRESS`, which defaults to localhost. Set it to a VPN interface address for private remote access. Clients must trust the local Caddy CA; no public TLS trust has been claimed by a local smoke test.

Production settings require secure HttpOnly cookies, HTTPS origins, a Fernet TOTP key and nondevelopment DB/MinIO credentials. PostgreSQL, MinIO, Valkey and the API have no public host ports. Prometheus and Grafana bind localhost only; use a VPN or SSH tunnel for administration. The operator keeps the production env file outside Git, stores a separate encrypted copy of the TOTP key and other secrets, and mounts an independent `BACKUP_ROOT` (NAS or other disk) before enabling use.

Start after replacing all placeholders in `ops/production.env.example`:

```text
docker compose -f docker-compose.prod.yml --env-file /secure/production.env config --quiet
docker compose -f docker-compose.prod.yml --env-file /secure/production.env up -d --build
docker compose -f docker-compose.prod.yml --env-file /secure/production.env exec -T api alembic upgrade head
```

The reverse proxy and monitoring configurations are reproducible in `ops/caddy`, `ops/prometheus` and `ops/grafana`. Verify Caddy, Prometheus and Grafana health as well as API readiness. TLS on a real VPN domain and browser CA trust require operator verification in that deployment; a localhost test does not prove them.

The one-shot `ca-export` service copies only the public Caddy root certificate into a read-only trust volume for backend services. If the CA rotates, rerun that service and restart the backend services before accepting requests. Frame protection, MIME sniffing protection and referrer policy are centralized in Caddy; HSTS applies to the configured host without imposing trust on sibling subdomains.

`ops/verify_production.py` verifies the TLS chain and hostname using a supplied public CA file (or system roots), Secure/HttpOnly login, the fixture value, blocked public metrics, an active Prometheus scrape and the provisioned Grafana dashboard. It reads a synthetic test password from `RESTORE_TEST_PASSWORD`; credentials and cookies are never printed. Run it against the target deployment after establishing client CA trust.
