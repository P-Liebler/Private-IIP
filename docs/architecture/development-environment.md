# Development environment

## Compose services and ports

| Service | Container port | Host binding | Readiness |
| --- | --- | --- | --- |
| web | 3000 | 127.0.0.1:3000 | HTTP homepage |
| api | 8000 | 127.0.0.1:8000 | `/api/v1/health/ready` |
| postgres | 5432 | none | `pg_isready` |
| valkey | 6379 | none | `valkey-cli ping` |
| minio | 9000/9001 | console 127.0.0.1:9001 | `mc ready local` |
| worker | none | none | Celery inspect ping |
| scheduler | none | none | Beat PID liveness |

PostgreSQL, Valkey, MinIO, web dependencies and Next.js development build output use named local volumes. Backend and frontend source directories are bind-mounted for development. Keeping `/app/.next` in its own volume prevents concurrent container and host builds from writing the same generated type files. The worker and API use the same backend image and package.

## Settings and environments

`.env.example` documents the `local` values. Copy it to `.env`; never commit the copy. `APP_ENV` accepts `local`, `test`, `staging` or `production`; only local/test are exercised in this phase. Staging and production need separate secrets, volumes and databases. `APP_DEBUG` is false by default, and production settings reject development credentials and plaintext MinIO transport.

The MinIO image is a pinned community build of the [October 2025 upstream security release](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z). The [official Docker Hub image](https://hub.docker.com/r/minio/minio/tags) stops at the earlier September release. Before a production deployment, verify the chosen image and its provenance again. Its console and application ports are local-only in this Compose file.

## Common operations

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose exec -T api alembic upgrade head
docker compose exec -T api python -m app.jobs.smoke
docker compose exec -T api python -m app.core.storage_smoke
docker compose run --rm api pytest -q
docker compose run --rm web npm run build
docker compose down
```

No external financial provider is called by this stack. The harmless Celery task verifies broker → worker → result backend. The object round trip verifies MinIO put/get/head and removes only its disposable smoke key.
