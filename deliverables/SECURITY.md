# SECURITY.md

Last updated: 2026-05-15

## 1. Security Goals

This is an internal authenticated document classification service. The security model for the Week 6 version targets:

- no secrets committed to Git
- all runtime secrets resolved from Vault at startup
- JWT-based authentication
- Casbin role-based authorization
- audit logging for every sensitive action
- hard refusal to start when required security dependencies are missing

## 2. Secret Handling

Secrets are never hardcoded in application code.

`.env` contains only bootstrap values needed to reach Vault and configure local ports. It never contains application secrets.

```env
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-only-root-token
API_PORT=8000
FRONTEND_PORT=3000
```

All application secrets are resolved from Vault at startup via `load_secrets()`.

**Verify no passwords in application code:**

```bash
grep -ri 'password' backend/app/
```

Expected: matches only in Vault-reading adapters (`infra/vault.py`, `infra/sftp.py`) and in library-required field names (`schemas/users.py`). No hardcoded credentials.

## 3. Vault KV v2 Layout

Secrets are stored under `secret/data/doc-classifier/` in Vault KV v2.

| Path | Contains |
|---|---|
| `secret/data/doc-classifier/jwt` | JWT signing secret, algorithm, token lifetime |
| `secret/data/doc-classifier/db` | Postgres database URL |
| `secret/data/doc-classifier/minio` | MinIO access key and secret key |
| `secret/data/doc-classifier/sftp` | SFTP username and password |
| `secret/data/doc-classifier/redis` | Redis connection URL |

These paths are seeded by `vault-init` at compose startup using the dev-only defaults from docker-compose environment variables.

## 4. Authentication

Authentication uses `fastapi-users` with JWT (Bearer transport).

Rules:
- JWT signing key resolves from Vault at startup.
- JWT payload does not contain sensitive information.
- Every protected route requires a valid Bearer token.
- Missing or invalid token → `401 Unauthorized`.
- Authenticated user without the required permission → `403 Forbidden`.
- Registration is admin-invite-only. There is no public `/auth/register` route.

## 5. Authorization

Authorization uses Casbin RBAC. Roles are stored in the Casbin grouping policy table only — not as a column on the user table.

| Role | Permissions |
|---|---|
| `admin` | Invite users, toggle roles, view audit log, view batches |
| `reviewer` | View batches, relabel low-confidence predictions (top-1 < 0.70) |
| `auditor` | Read-only access to batches and audit log |

Role change flow:
1. Admin calls `PUT /admin/users/{user_id}/roles/{role}`.
2. Service layer verifies the actor is admin.
3. Service layer checks the last-admin guard (409 if only one admin remains).
4. Casbin grouping policy is updated.
5. Audit log entry is written.
6. Affected user's `/me` cache is invalidated.
7. Target user sees updated permissions on next page load — no logout required.

## 6. Audit Log

Every sensitive action writes an audit log row.

Audited actions:
- `role_change` — every assignment or removal of a role
- `relabel` — every reviewer relabel of a prediction
- `batch_state_change` — every batch state transition

Audit log fields: actor user ID, action, target type, target ID, before value, after value, request ID, timestamp.

The audit log is append-only. Entries are never deleted or updated by the application.

## 7. Startup Security Checks

**API refuses to start if:**
- Vault is unreachable
- Required Vault KV paths are missing or empty
- Casbin policy table is empty
- `classifier.pt` is missing
- `classifier.pt` SHA-256 does not match `model_card.json`
- `model_card.json` `test_top1` is below 0.70

**Worker refuses to start if:**
- `classifier.pt` is missing
- SHA-256 mismatch
- `test_top1` below threshold

**To demonstrate this during the demo:**

```bash
# Stop Vault, then try to restart the API
docker compose stop vault
docker compose restart api
docker compose logs api  # should show Vault unreachable error and exit
```

## 8. Request ID Traceability

Every API request is tagged with a `request_id` (UUID v4) from the `X-Request-ID` header or generated at the middleware layer. SFTP-originated jobs generate their own request IDs in `sftp-ingest`.

The request ID propagates through:
- structured JSON logs in api, worker, sftp-ingest
- queue payload
- `batches.request_id`
- `predictions.request_id`
- `audit_log.request_id`

## 9. Out of Scope for Week 6

The following are important in production but not targeted in this version:

- IP allowlisting / rate limiting
- Refresh token rotation
- Audit log retention policy
- Production Vault hardening (TLS, unsealing, token scoping)
- Multi-tenant support
- Public cloud deployment security
