# ADR-009: Server-side session authentication

**Status:** Accepted  
**Date:** 2026-10-03

## Context

The platform is initially a private browser application. It needs prompt revocation, optional TOTP, and no public identity provider. The existing PostgreSQL and Valkey services are available.

## Decision

Use Argon2id password verification followed by optional TOTP, then a random token in an HttpOnly cookie. Store only the token hash and session state in PostgreSQL. Use Valkey for rate limits and temporary TOTP challenges. Protect writes with restricted CORS, SameSite cookies and Origin/Fetch Metadata checks. Encrypt TOTP secrets with an environment-provided Fernet key.

Security state changes and audit events share a database transaction and fail together. Failed-login audit writes are best effort, logged on failure; invalid credentials remain invalid. TOTP reset is an administrative CLI action that revokes sessions.

## Consequences

The database must be reachable for authenticated requests, and Valkey for login. Sessions can be revoked immediately and audited. The browser needs no token storage. A protected backup of the TOTP encryption key is required. Production needs HTTPS and a secure cookie; final ingress and backup/restore deployment remain later milestones.
