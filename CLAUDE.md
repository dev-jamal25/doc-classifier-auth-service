# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

It is the project-level knowledge base. Read this before planning or editing code.

---

## Current State

The repository is in early implementation/scaffolding mode.

The project skeleton, Docker Compose service list, CI workflow, architecture docs, and delivery docs exist. Most application logic is still being built incrementally.

Assume a feature is unbuilt unless real code exists for it.

Before making non-trivial changes, read the architecture and decision docs:

- `ARCH.md` or `deliverables/ARCH.md`
- `DECISIONS.md` or `deliverables/DECISIONS.md`
- `RUNBOOK.md` or `deliverables/RUNBOOK.md`
- `SECURITY.md` or `deliverables/SECURITY.md`
- `COLLABORATION.md` or `deliverables/COLLABORATION.md`
- `LICENSES.md` or `deliverables/LICENSES.md`

If both root-level docs and `deliverables/` docs exist, prefer the docs that the README points to as the current source of truth.

---

## Project Summary

This project is **Project 6: Document Classifier as an Authenticated Service**.

It is an internal document classification service.

A scanner/vendor drops grayscale TIFF documents into an SFTP folder. An ingestion pipeline picks up those files, uploads them to blob storage, queues classification jobs, and an inference worker classifies each document against the RVL-CDIP document layout classes.

Authenticated users browse, review, and relabel predictions through a permission-gated FastAPI API.

The full stack runs locally through Docker Compose.

---

## What This Project Is Not

This is **not OCR**.

Do not extract document text.

The classifier predicts the visual/layout class of a document, not the text content inside the document.

---

## Dataset Context

Dataset: RVL-CDIP

Document layout classes:

- letter
- form
- email
- handwritten
- advertisement
- scientific_report
- scientific_publication
- specification
- file_folder
- news_article
- budget
- invoice
- presentation
- questionnaire
- resume
- memo

The full RVL-CDIP dataset must not be committed to the repository.

Training, full test-set evaluation, and golden-set selection happen in Colab.

Only the required artifacts ship to the repo.

Expected classifier artifact paths:

```text
backend/app/classifier/models/classifier.pt
backend/app/classifier/models/model_card.json
backend/app/classifier/eval/golden_images/
backend/app/classifier/eval/golden_expected.json
backend/app/classifier/eval/golden.py
```

Model weights should be tracked with Git LFS.

---

## Full System Architecture

Main services:

| Service | Purpose |
|---|---|
| `api` | FastAPI app for auth, RBAC, batch browsing, prediction review, role management, audit log access. |
| `worker` | RQ inference worker. Consumes jobs, runs classifier inference, writes predictions, writes overlay output, invalidates caches through services. |
| `sftp-ingest` | Polls SFTP, validates files, uploads raw documents to MinIO, creates batches, enqueues jobs. |
| `migrate` | Runs Alembic migrations and exits before the API starts. |
| `db` | Postgres 16 application database. |
| `redis` | Redis backend for RQ and API cache. |
| `minio` | S3-compatible blob storage for raw TIFFs and overlay PNGs. |
| `sftp` | SFTP drop target for scanner/vendor files. |
| `vault` | HashiCorp Vault dev mode for local secrets. |

Primary data flow:

```text
scanner/vendor
  -> SFTP
  -> sftp-ingest
  -> MinIO raw document storage
  -> Redis/RQ job
  -> worker
  -> classifier inference
  -> Postgres prediction row
  -> MinIO overlay PNG
  -> FastAPI reads
  -> authenticated user review
```

---

## Backend Layer Boundary

The backend is strictly layered.

All backend code lives under `backend/app/`.

```text
backend/app/
├── api/             # HTTP routers, request/response schemas, route dependencies
├── services/        # business logic, transaction boundaries, cache invalidation
├── repositories/    # SQL through async SQLAlchemy
├── domain/          # Pydantic domain models, enums, internal contracts
├── infra/           # external adapters: Vault, Redis/RQ, MinIO, SFTP, cache, model artifacts
├── db/              # SQLAlchemy ORM, session factory, Alembic migrations
├── classifier/      # model artifacts and golden-set replay files
└── core/            # config, logging, app setup, shared errors
```

The boundary must not be crossed.

| Layer | Owns | Must NOT do |
|---|---|---|
| `app/api/` | HTTP routers, request/response schemas, auth dependencies, status codes | No SQLAlchemy queries, no Redis, no MinIO, no Vault, no cache invalidation, no business logic |
| `app/services/` | Business logic, workflows, transaction boundaries, cache invalidation | No `HTTPException` as normal business logic, no FastAPI `Request`, no route-specific assumptions |
| `app/repositories/` | SQL reads/writes through async SQLAlchemy sessions | No cache invalidation, no HTTP errors, no external systems, no business decisions |
| `app/domain/` | Pydantic models, enums, internal contracts | No DB sessions, no HTTP concepts, no external clients |
| `app/infra/` | External adapters for Vault, Redis/RQ, MinIO, SFTP, cache, model artifact validation | No business rules beyond adapter-level error wrapping |
| `app/db/` | ORM models, database session factory, Alembic migrations | Imported only by repositories and DB setup |

Important:

- Cache invalidation lives in `app/services/` only.
- Repositories do SQL only.
- Routers call services, not repositories directly.
- API routes do not touch external systems directly.
- ORM models are not returned directly from API routes.
- Services should be callable from both API routes and background workers.

---

## Team Ownership Boundaries

The team has 3 members.

### Service/API owner

Owns:

- FastAPI app foundation
- API routes
- service layer
- repository layer
- domain schemas
- DB models and migrations
- audit log table and service logic
- auth integration later
- Casbin RBAC later
- cache invalidation calls in service layer later
- endpoint assertions for smoke tests

### Ingestion/Infra owner

Owns:

- `backend/app/infra/`
- Vault setup
- Redis/RQ setup
- cache adapter implementation
- SFTP watcher
- MinIO/blob adapter
- queue adapter
- ingestion worker
- inference worker integration
- SFTP-to-API smoke test lead

### Classifier owner

Owns:

- Colab training
- ConvNeXt model fine-tuning
- `classifier.pt`
- `model_card.json`
- SHA-256 generation
- full test-set metrics
- golden image set
- golden expected outputs
- golden-set replay support

### Shared ownership

Shared files require care:

- `docker-compose.yml`
- `.env.example`
- `.github/workflows/*`
- backend dependency files
- project docs
- smoke/integration tests

Avoid broad changes to shared files unless the task requires it.

---

## Frozen Project Decisions

| Topic | Decision |
|---|---|
| Team size | 3 people |
| Branch naming | `feat/...` is acceptable instead of `feature/...` |
| Registration flow | Admin-invite-only |
| Role storage | Casbin grouping policy only |
| Model card schema | Temporary permissive Pydantic schema: required known fields, allow extra fields |
| Model threshold | `test_top1 >= 0.80` |
| Max SFTP file size | `50MB` |
| Malformed SFTP drops | Create failed batch rows in Postgres |
| Failed SFTP attribution | `source = "sftp-ingest"`, `created_by_user_id = null` |
| Cache TTLs | `/me = 300s`, `/batches = 60s`, `/batches/{batch_id} = 60s`, `/predictions/recent = 60s` |
| Last-admin protection | Count admins through Casbin grouping policy before demotion |
| SFTP-to-API smoke test | Infra/worker owner leads; API owner supports final API assertion |
| Queue payload shape | `batch_id`, `blob_key`, `source_filename`, `sftp_user`, `request_id`, `received_at` |

Do not silently change these decisions. If a task requires changing one, update `DECISIONS.md`.

---

## Core Database Concepts

### `batches`

Represents an ingested document/batch unit.

Expected fields:

- `id`
- `source_filename`
- `source`
- `sftp_user`
- `blob_key`
- `state`
- `failure_reason`
- `request_id`
- `created_by_user_id`
- `created_at`
- `updated_at`

Expected states:

```text
pending
processing
completed
failed
```

Notes:

- `created_by_user_id` is nullable.
- For SFTP-created batches, use `created_by_user_id = null`.
- For malformed SFTP drops, use `state = "failed"` and set `failure_reason`.

### `predictions`

Stores model output for a document/batch.

Expected fields:

- `id`
- `batch_id`
- `label`
- `confidence`
- `top5_labels`
- `top5_confidences`
- `overlay_blob_key`
- `model_sha256`
- `reviewed_by_user_id`
- `reviewed_label`
- `reviewed_at`
- `request_id`
- `created_at`

Notes:

- `top5_labels` and `top5_confidences` may be JSON columns.
- `reviewed_by_user_id` is nullable until a reviewer relabels.
- Reviewers may relabel only when top-1 confidence is below `0.7`.

### `audit_log`

Records sensitive system actions.

Expected fields:

- `id`
- `actor_user_id`
- `action`
- `target_type`
- `target_id`
- `before_value`
- `after_value`
- `request_id`
- `created_at`

Expected audit actions:

```text
role_change
relabel
batch_state_change
```

Notes:

- `actor_user_id` is nullable for system-originated events.
- Role changes, relabels, and batch state changes must be auditable.

### Casbin policy table

Casbin owns its own policy table.

Do not invent a separate `role` column or `user_roles` table unless the team explicitly changes D-004.

---

## Queue Payload Contract

The ingestion worker enqueues jobs shaped like this:

```json
{
  "batch_id": "uuid",
  "blob_key": "batches/2026/05/13/abc123.tif",
  "source_filename": "scan_001.tif",
  "sftp_user": "vendor-1",
  "request_id": "uuid",
  "received_at": "2026-05-13T14:22:00Z"
}
```

The worker needs at minimum:

- `batch_id`
- `blob_key`
- `request_id`

Other fields are useful for logs and debugging.

---

## Worker-to-Service Contract

The worker must not write directly to repositories or invalidate cache directly.

The worker records inference output through a service-layer entrypoint such as:

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
- audit behavior if needed
- cache invalidation when cache adapter exists

This keeps API writes and worker writes consistent.

---

## Auth and RBAC Plan

Authentication:

- `fastapi-users`
- JWT
- JWT signing key from Vault
- admin-invite-only registration

Authorization:

- Casbin
- roles stored through Casbin grouping policy only
- roles: `admin`, `reviewer`, `auditor`

Role permissions:

| Role | Can do |
|---|---|
| `admin` | Invite users, toggle roles, view audit log, view batches |
| `reviewer` | View batches, relabel predictions where confidence `< 0.7` |
| `auditor` | Read-only access to batches and audit log |

Auth status rules:

- Missing/invalid token: `401 Unauthorized`
- Authenticated but not allowed: `403 Forbidden`

Last-admin rule:

- Before demoting an admin, count current admins through Casbin grouping policy.
- If only one admin exists, block the demotion.

Do not add public registration unless the decision is explicitly changed.

---

## Cache Plan

Cache backend: Redis through `fastapi-cache2`.

Required cached endpoints:

| Endpoint | TTL |
|---|---:|
| `GET /me` | 300s |
| `GET /batches` | 60s |
| `GET /batches/{batch_id}` | 60s |
| `GET /predictions/recent` | 60s |

Invalidation map:

| Cached endpoint | Invalidated by |
|---|---|
| `GET /me` | Role change targeting that user |
| `GET /batches` | New batch, batch state change |
| `GET /batches/{batch_id}` | Batch state change, prediction write, relabel |
| `GET /predictions/recent` | New prediction write, relabel |

Rule:

- Cache invalidation belongs in `app/services/`.
- Do not invalidate cache in routers.
- Do not invalidate cache in repositories.

---

## Vault and Secret Handling

Secrets resolve from Vault at startup.

Local `.env` should contain only bootstrap values needed for local dev, such as:

- Vault address
- Vault token
- local port mappings

Application secrets should be pulled from Vault, not hardcoded.

Expected secret categories:

- JWT signing key
- Postgres credentials/URL
- MinIO credentials
- SFTP credentials
- Redis connection information if needed

Do not scatter `os.getenv()` calls across the app.

Use a centralized config/bootstrap pattern.

Do not commit `.env`.

Do not hardcode secrets.

---

## Startup and Refuse-to-Start Checks

The API refuses to start if:

- Vault is unreachable
- required Vault secrets are missing
- Casbin policy table is empty
- classifier weights are missing
- `classifier.pt` SHA-256 does not match `model_card.json`
- model card `test_top1 < 0.80`

The worker refuses to start if:

- classifier weights are missing
- `classifier.pt` SHA-256 does not match `model_card.json`
- model card `test_top1 < 0.80`

Startup failures should be loud and clear.

Do not allow the system to fail later on the first request when a required dependency is missing.

---

## Logging and Request IDs

Use structured JSON logs.

No `print()` in runtime paths.

Minimum log fields:

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

Request ID rules:

- API accepts or generates `X-Request-ID`.
- SFTP ingestion generates a UUID v4 request ID for ingestion-originated jobs.
- Queue payload includes `request_id`.
- Worker logs include `request_id`.
- DB rows include `request_id` where relevant:
  - `batches.request_id`
  - `predictions.request_id`
  - `audit_log.request_id`

---

## Docker Compose Expectations

The stack should come up from a fresh clone with:

```bash
cp .env.example .env
docker compose up --build
```

Expected services:

- api
- worker
- sftp-ingest
- migrate
- db
- redis
- minio
- sftp
- vault

The `migrate` service runs Alembic migrations and exits before the API boots.

Do not require manual commands to start core dependencies unless documented in `RUNBOOK.md`.

---

## CI Expectations

CI should eventually include:

- lint
- format check
- type check
- unit tests
- golden-set replay test
- Docker image build
- compose smoke test
- SFTP drop -> API-visible prediction assertion

If CI jobs are placeholders, do not treat green CI as proof that the system is production-ready.

---

## Frontend Context

The frontend may be a stub or still undecided.

Do not make assumptions about frontend framework unless the repository contains a finalized frontend implementation or decision doc.

The core Week 6 architecture is backend/worker/infrastructure heavy.

---

## Common Commands

Prefer `uv`.

Backend commands usually run from `backend/`.

```bash
uv sync
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
uv run ruff format --check .
uv run mypy app/
uv run pytest -q
```

Local stack from repo root:

```bash
cp .env.example .env
docker compose up --build
```

Use the commands already configured in `pyproject.toml`, CI, or README if they differ.

---

## Coding Standards

Use:

- Python 3.12 unless the repo config says otherwise
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x async
- Alembic
- RQ, not Celery
- Redis
- MinIO
- HashiCorp Vault dev mode
- Casbin
- `fastapi-users`
- `fastapi-cache2`
- PyTorch / torchvision for classifier worker only

Rules:

- async routes only
- no blocking I/O in request paths
- no `requests` in async code
- no `time.sleep()` in async code
- no `print()` in runtime paths
- no secrets in code
- no `.env` committed
- no business logic in routers
- no SQL outside repositories
- no cache invalidation outside services
- no ORM objects returned directly from API routes
- type hints on functions
- Pydantic at boundaries
- external calls need timeout/retry when implemented
- tests for critical paths

---

## File and Naming Conventions

Use descriptive names.

Good:

```text
batch_service.py
prediction_service.py
audit_repository.py
record_prediction
create_failed_batch
list_recent_predictions
```

Avoid vague files:

```text
utils.py
helpers.py
misc.py
stuff.py
manager.py
process_data
```

If a file cannot be described in one sentence, split it.

---

## How Claude Code Should Work in This Repo

Before editing:

1. Read this file.
2. Read relevant architecture/decision docs.
3. Identify the current branch and task scope.
4. Check ownership boundaries.
5. Plan a small change.
6. Avoid unrelated refactors.

When editing:

1. Respect the layer boundary.
2. Avoid touching teammate-owned files unless required.
3. Keep changes focused.
4. Do not invent new architecture.
5. Do not silently add dependencies.
6. Add tests when practical.
7. Keep TODOs explicit and tied to deferred dependencies.

After editing, always report:

```text
Summary:
- ...

Files changed:
- ...

Tests:
- ...

Deferred:
- ...

Next suggested step:
- ...
```

---

## Things Not To Do

Do not:

- implement OCR
- make the API run PyTorch inference
- bypass the service layer from the worker
- store roles in a user table column unless the decision changes
- add public registration unless the decision changes
- invalidate cache from routers or repositories
- let malformed SFTP files disappear silently
- hardcode secrets
- commit full RVL-CDIP dataset
- commit `.env`
- return ORM models directly from API routes
- add broad “helper” files without clear ownership
- change frozen decisions without updating `DECISIONS.md`
