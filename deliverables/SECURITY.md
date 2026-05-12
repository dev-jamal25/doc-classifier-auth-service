# SECURITY.md

Status: Temporary baseline for team review
Last updated: 2026-05-12

## 1. Security Goals

This project is an internal authenticated document classification service. The main security goals for the Week 6 version are:

- no secrets committed to Git
- secrets resolved from Vault at startup
- JWT-based authentication
- Casbin role-based authorization
- audit logging for sensitive actions
- clear refusal to start when required security dependencies are missing

## 2. Secret Handling

Secrets are not hardcoded in application code.

Local `.env` should contain only bootstrap values needed to reach Vault and local port configuration.

Example bootstrap values:

```env
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-only-root-token
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379
MINIO_PORT=9000
SFTP_PORT=2222
```

All application secrets should be read from Vault at startup.

## 3. Temporary Vault KV v2 Layout

Proposed paths:

```text
secret/data/doc-classifier/jwt
secret/data/doc-classifier/db
secret/data/doc-classifier/minio
secret/data/doc-classifier/sftp
secret/data/doc-classifier/redis
```

Proposed secret groups:

| Path | Contains |
|---|---|
| `secret/data/doc-classifier/jwt` | JWT signing secret, token lifetime settings. |
| `secret/data/doc-classifier/db` | Postgres username, application database name, connection password/URL. |
| `secret/data/doc-classifier/minio` | MinIO access key and secret key. |
| `secret/data/doc-classifier/sftp` | SFTP username and credential used by the local dev SFTP container. |
| `secret/data/doc-classifier/redis` | Redis connection information if needed. |

Final paths may change after implementation.

## 4. Authentication

Authentication will use `fastapi-users` with JWT.

Rules:

- JWT signing key resolves from Vault at startup.
- JWT payload must not contain sensitive information.
- Protected routes require a valid bearer token.
- Missing or invalid token returns `401 Unauthorized`.
- Authenticated user without permission returns `403 Forbidden`.

## 5. Authorization

Authorization uses Casbin RBAC.

Roles:

| Role | Permission Summary |
|---|---|
| `admin` | Invite users, toggle roles, view audit log. |
| `reviewer` | View batches and relabel low-confidence predictions. |
| `auditor` | Read-only access to batches and audit log. |

Role changes must:

1. verify the actor is an admin
2. update the target user role/policy
3. write an audit log row
4. invalidate affected caches

## 6. Audit Log Scope

The audit log records:

- actor
- action
- target type
- target ID
- before value
- after value
- timestamp
- request ID

Actions to audit:

- every role change
- every relabel
- every batch state change

## 7. Startup Security Checks

The API refuses to start if:

- Vault is unreachable
- required Vault secrets are missing
- Casbin policy table is empty
- classifier artifact integrity checks fail

The worker refuses to start if classifier artifact integrity checks fail.

## 8. Secrets Search Rule

The project should pass this check before demo:

```bash
grep -ri 'password' backend/app/
```

Expected result: no matches outside the Vault-reading code or safe field names that are required by libraries.

## 9. Out of Scope for Week 6

These are important in production but not targeted for the current bootcamp scope unless time allows:

- public cloud deployment hardening
- IP allowlisting
- rate limiting
- full refresh-token rotation
- audit log retention policy
- production Vault configuration
- multi-tenant organization support
