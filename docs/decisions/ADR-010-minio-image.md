# ADR-010: Pinned patched MinIO container for local development

**Status:** Accepted for local foundation; recheck before production  
**Date:** 2026-10-03

The Compose stack uses [`coollabsio/minio:RELEASE.2025-10-15T17-29-55Z`](https://hub.docker.com/r/coollabsio/minio/tags), a community container built from the upstream October 2025 security release. The [upstream release](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) documents the fix; the [official Docker Hub tags](https://hub.docker.com/r/minio/minio/tags) stop at the earlier September release. Docker Hub was selected after the same tag on GHCR could not be downloaded in the development environment. The downloaded container reports the expected upstream release version. Verify image provenance and current maintenance before using it outside the local development environment.
