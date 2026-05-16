# ARCH.md

Project: Document Classifier as an Authenticated Service
Last updated: 2026-05-15

## 1. System Overview

This project is an internal document classification service. A scanner vendor drops grayscale TIFF documents into an SFTP folder. The ingestion pipeline stores the files, queues classification work, and an inference worker classifies each document against the 16 RVL-CDIP layout classes. Authenticated users then browse batches, review predictions, and relabel low-confidence predictions through a permission-gated FastAPI API.

This is not an OCR system. We classify the visual document layout, not the document text.

```text
Scanner Vendor
     |
     v
atmoz/sftp
     |
     v
sftp-ingest worker
     |
     +--> MinIO raw document storage
     |
     +--> Redis / RQ classification job
              |
              v
        inference worker
              |
              +--> loads classifier.pt
              +--> writes prediction row to Postgres
              +--> writes overlay PNG to MinIO
              +--> invalidates affected Redis caches
                       |
                       v
FastAPI API <---- Postgres / Redis / Vault / Casbin
     |
     v
Authenticated users: admin, reviewer, auditor
```

## 2. Main Runtime Services

| Service | Purpose |
|---|---|
| `api` | FastAPI application for authentication, RBAC, batch browsing, relabeling, and audit log access. The API does not run inference. |
| `worker` | RQ inference worker. Consumes Redis jobs, runs classifier inference, stores predictions, and invalidates caches through the service layer. |
| `sftp-ingest` | Polls the SFTP folder, uploads incoming TIFF files to MinIO, creates batches, and enqueues classification jobs. |
| `migrate` | Runs Alembic migrations and exits before the API starts. |
| `db` | Postgres 16 application database. |
| `redis` | Redis backend for RQ queue and fastapi-cache2. |
| `minio` | S3-compatible blob storage for raw TIFFs and overlay PNGs. |
| `sftp` | SFTP drop target for scanner-vendor input. |
| `vault` | HashiCorp Vault dev server for local secret resolution. |

## 3. Repository and Backend Layering

The backend is intentionally layered. This boundary is frozen unless the team explicitly agrees to change it.

```text
backend/app/
├── api/             # HTTP routers, request/response schemas, route dependencies
├── services/        # Business logic, transaction boundaries, cache invalidation
├── repositories/    # SQL-only data access
├── domain/          # Pydantic domain models, enums, internal contracts
├── infra/           # External adapters: Vault, Redis/RQ, MinIO, SFTP, cache
├── db/              # SQLAlchemy ORM models, sessions, Alembic migrations
├── classifier/      # Classifier artifacts and golden-set replay files
└── core/            # Config, logging, startup/lifespan, shared errors
```

## 4. Layer Boundary Rules

| Layer | Owns | Must Not Do |
|---|---|---|
| `app/api/` | HTTP concerns only: routers, status codes, request/response models, auth dependencies. | No SQLAlchemy queries, no Redis calls, no MinIO calls, no Vault calls, no direct cache invalidation. |
| `app/services/` | Business rules, transaction boundaries, permission-aware workflows, cache invalidation. | No HTTPException as business logic, no route-specific assumptions, no FastAPI `Request` dependency. |
| `app/repositories/` | SQL reads/writes through SQLAlchemy async sessions. | No cache invalidation, no HTTP errors, no external systems, no business decisions. |
| `app/domain/` | Pydantic domain models, enums, service/repository contracts. | No database sessions, no HTTP concepts, no external clients. |
| `app/infra/` | Adapters for Vault, Redis/RQ, MinIO, SFTP, cache, classifier artifact checks. | No business rules beyond adapter-level error wrapping. |
| `app/db/` | ORM models, database session factory, Alembic migrations. | Imported only by repositories and DB setup code. |

## 5. Core Data Flow: SFTP Drop to Prediction

1. Scanner vendor drops a TIFF file into the SFTP input folder.
2. `sftp-ingest` polls the folder and detects the new file within the agreed polling window.
3. `sftp-ingest` validates the file at a basic level:
   - not empty
   - expected image extension/content type
   - maximum size: `50MB`
4. `sftp-ingest` uploads the raw file to MinIO.
5. `sftp-ingest` creates or updates a `batches` row through the service layer.
6. `sftp-ingest` enqueues a Redis/RQ job with:
   - `batch_id`
   - `blob_key`
   - `source_filename`
   - `request_id`
7. `worker` consumes the job.
8. `worker` loads the classifier artifact, runs inference, and creates an overlay PNG.
9. `worker` calls `prediction_service.record_prediction(...)`.
10. `prediction_service` writes the prediction row, updates batch state if needed, writes audit/cache effects, and invalidates affected cached reads.
11. Users see the result through `GET /batches/{bid}` or `GET /predictions/recent`.

Malformed SFTP drops are not ignored. The ingestion worker creates a failed batch record in Postgres, logs the failure reason, and moves the file to quarantine when possible. Because SFTP drops do not pass through an authenticated API route, the batch stores `source = "sftp-ingest"` and `created_by_user_id = null`.

## 6. API Does Not Run Inference

The API is responsible for authentication, authorization, reads, review actions, audit access, and orchestration. It never loads the PyTorch model for request-time inference. Inference is isolated in the worker.

Reason: API requests should remain fast and predictable. Model inference is CPU-heavy and belongs in the worker path.

## 7. Authentication and Authorization

Authentication is handled with `fastapi-users` and JWT.

Registration is **admin-invite-only**. Users should not self-register publicly in the final flow unless the team temporarily enables it only for local development.

Authorization is handled with Casbin RBAC.

User roles are stored through **Casbin grouping policy only**. We do not keep a separate role column or role join table unless implementation proves that fastapi-users integration requires a minimal support field.

| Role | Permissions |
|---|---|
| `admin` | Invite users, toggle roles, view audit log, view batches. |
| `reviewer` | View batches and relabel predictions only when top-1 confidence is below `0.7`. |
| `auditor` | Read-only access to batches and audit log. |

The role-toggle flow is the central permission story:

1. Admin calls the role-toggle endpoint.
2. Service layer validates the actor and target.
3. Service layer checks whether the action would remove the last remaining admin.
4. If only one admin exists, that admin cannot be demoted.
5. Service layer updates the Casbin grouping policy.
6. Service layer writes an audit log entry.
7. Service layer invalidates affected user permission/cache entries.
8. Target user sees updated permissions on next page load without logout/login.

## 8. Endpoint Inventory

| Method | Endpoint | Roles | Notes |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Form-encoded `username` + `password`. Returns JWT access token. |
| `POST` | `/auth/logout` | Authenticated | Stateless — instructs clients to discard their token. |
| `GET` | `/me` | Authenticated | Current user profile and Casbin roles. Cached 300 s. |
| `GET` | `/healthz` | Public | API liveness check. |
| `GET` | `/batches` | admin, reviewer, auditor | Paginated batch list. Cached 60 s. |
| `GET` | `/batches/{batch_id}` | admin, reviewer, auditor | Single batch. Cached 60 s. |
| `GET` | `/predictions/recent` | admin, reviewer, auditor | Recent predictions. Cached 60 s. |
| `PATCH` | `/predictions/{prediction_id}/review` | reviewer | Relabel only when top-1 confidence `< 0.7`. |
| `POST` | `/admin/users/invite` | admin | Create user (invite-only registration). |
| `PUT` | `/admin/users/{user_id}/roles/{role}` | admin | Assign role. Writes audit log. Invalidates `/me` cache. |
| `DELETE` | `/admin/users/{user_id}/roles/{role}` | admin | Remove role. Last-admin guard returns 409. |
| `GET` | `/admin/audit-log` | admin | Read audit log entries. |

## 9. Cache Plan

fastapi-cache2 uses Redis as the cache backend.

A cache TTL is the maximum time a cached response can live before Redis expires it automatically. We still invalidate caches immediately on writes, but the TTL is a safety net in case an invalidation bug or missed edge case happens.

| Cached Read | Frozen TTL | Invalidated By | Reason |
|---|---:|---|---|
| `GET /me` | 300s | Role change targeting that user. | User profile changes rarely, but role changes still invalidate immediately. |
| `GET /batches` | 60s | New batch, batch state change. | Batch list changes during ingestion, so the cache should be short-lived. |
| `GET /batches/{batch_id}` | 60s | State change for that batch, prediction write for that batch, relabel for that batch. | Batch detail changes as predictions arrive. |
| `GET /predictions/recent` | 60s | New prediction write, relabel. | Recent predictions change often during demos and ingestion. |

Rule: cache invalidation lives in `app/services/`, never in routers or repositories.

## 10. Startup and Refuse-to-Start Checks

The stack boot sequence is:

1. `vault` starts in dev mode.
2. `db`, `redis`, `minio`, and `sftp` start.
3. `migrate` runs `alembic upgrade head` and exits.
4. `api` starts only after required dependencies are available.
5. `worker` and `sftp-ingest` start.

The API refuses to start if:

- Vault is unreachable.
- Casbin policy table is empty.
- Classifier weights are missing.
- `classifier.pt` SHA-256 does not match `model_card.json`.
- Model card `test_top1` is below the threshold committed in the README.

The worker refuses to start if:

- Classifier weights are missing.
- `classifier.pt` SHA-256 does not match `model_card.json`.
- Model card `test_top1` is below the threshold committed in the README.

Startup threshold: `test_top1 >= 0.70`. Actual classifier score: 0.8029.

## 11. Classifier Artifact Contract

Expected paths:

```text
backend/app/classifier/models/classifier.pt
backend/app/classifier/models/model_card.json
backend/app/classifier/eval/golden_images/
backend/app/classifier/eval/golden_expected.json
backend/app/classifier/eval/golden.py
```

Temporary `model_card.json` shape.

For now, the service uses a permissive Pydantic schema that accepts the known required fields and allows extra fields from the classifier owner. This prevents the API/worker startup checks from blocking while the classifier owner finalizes the model card format.

```json
{
  "sha256": "TO_BE_FILLED",
  "backbone": "convnext_tiny",
  "weights_enum": "IMAGENET1K_V1",
  "freeze_policy": "partial_unfreeze",
  "test_top1": 0.0,
  "test_top5": 0.0,
  "per_class_accuracy": {},
  "trained_at": "TO_BE_FILLED",
  "env_fingerprint": {}
}
```

## 12. Worker-to-Service Contract

The inference worker must not write directly to repositories or invalidate caches directly. It calls a service function.

Temporary contract:

```python
async def record_prediction(
    *,
    batch_id: UUID,
    label: str,
    confidence: float,
    top5: list[tuple[str, float]],
    overlay_blob_key: str,
    model_sha256: str,
    request_id: str,
) -> Prediction:
    ...
```

This service method owns:

- prediction insert
- batch state update if needed
- audit log if needed
- cache invalidation for affected reads

## 13. Request ID Propagation

Format: UUID v4 string.

Sources:

- API requests accept or generate `X-Request-ID`.
- SFTP-originated jobs generate a new request ID in `sftp-ingest`.

Propagation path:

```text
HTTP header or sftp-ingest generated value
 -> structured logs
 -> queue payload
 -> worker logs
 -> batches.request_id
 -> predictions.request_id
 -> audit_log.request_id
```

## 14. Logging

All services log structured JSON.

Minimum fields:

```json
{
  "timestamp": "ISO-8601",
  "level": "info",
  "service": "api | worker | sftp-ingest",
  "event": "snake_case_event_name",
  "request_id": "uuid-v4",
  "user_id": "optional-authenticated-user-id"
}
```

No `print()` statements in runtime paths.

## 15. Frozen Team Decisions

These are temporarily frozen for implementation and can be changed only after team review.

| Question | Frozen Decision |
|---|---|
| Team size | 3 people. |
| Registration flow | Admin-invite-only. |
| Role storage | Casbin grouping policy only. |
| Model card schema | Temporary permissive Pydantic schema: required known fields, allow extra fields. |
| Model threshold | `test_top1 >= 0.80`. |
| Max SFTP file size | `50MB`. |
| Malformed SFTP drops | Create failed batch rows and link them to the ingestion/system user where applicable. |
| Cache TTLs | `/me = 300s`; `/batches = 60s`; `/batches/{batch_id} = 60s`; `/predictions/recent = 60s`. |
| Last-admin protection | Count current admins from Casbin grouping policy. If only one admin exists, block demotion. |
| SFTP-to-API smoke test owner | Infra/worker owner leads it, with API owner supporting endpoint assertions. |
| Queue payload shape | `batch_id`, `blob_key`, `source_filename`, `sftp_user`, `request_id`, `received_at`. |

## 16. Frontend

The React/Vite/TypeScript console runs on port 3000 (Docker) or 5173 (local dev). In Docker it is served by nginx, which proxies all API paths (`/auth`, `/me`, `/batches`, `/predictions`, `/admin`) to the `api` service internally. The browser never talks directly to port 8000 in the production compose configuration.

The frontend falls back to curated mock data if the API is unreachable, which allows the UI to be developed and reviewed independently of the backend stack.
