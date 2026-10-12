# ADR-015: Backup and restore gate

**Status:** Accepted for P4, 2026-10-12.

V1 backup sets contain a PostgreSQL custom-format dump, immutable MinIO raw objects and a checksum manifest. The destination is configurable; production points it at an independent protected mount. Daily backup scheduling is delegated to the host scheduler. The default optional retention keeps seven daily, four weekly and six monthly successful sets. Secrets and TOTP encryption material are backed up separately, never in the application set.

V1 production acceptance requires a real isolated restore into new PostgreSQL and MinIO instances and verification of migration head, raw hash, login and a known portfolio value. A failed or unrun restore leaves the production gate open. The procedure records UTC success/failure for monitoring and removes the isolated test volumes afterward.
