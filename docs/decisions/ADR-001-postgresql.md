# ADR-001: PostgreSQL with pgvector

**Status:** Accepted for the foundation  
**Date:** 2026-10-03

Use one PostgreSQL database and enable pgvector through Alembic. The initial migration creates the extension only. Future domain tables, time partitioning and embeddings are added by later migrations; no `create_all()` path substitutes for migrations. This keeps operations simple for one self-hosted VM while retaining the planned vector capability.
