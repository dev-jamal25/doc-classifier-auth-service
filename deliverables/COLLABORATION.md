# COLLABORATION.md

Last updated: 2026-05-15

## Trello Board

Trello: 
**
Full team board: (https://trello.com/b/shmrnXK6/day-0)**
Individual boards:
https://trello.com/b/57SbBVlf/charbel
https://trello.com/b/qhUByHL0/jamal
https://trello.com/b/0JANqAYD/dina

Cards moved through: `To Do → In Progress → Review → Done`

## Team Ownership

| Area | Owner |
|---|---|
| Classifier — ConvNeXt training, model card, golden set, frontend console | Dina |
| API / service architecture — FastAPI routes, layered backend, auth, RBAC, services, repositories, cache invalidation, audit log, startup checks | Jamal |
| Ingestion and inference workers — SFTP polling, MinIO upload, Redis/RQ queue, worker inference path, overlay write, worker logs | [Teammate 3] |
| CI / smoke tests / integration support | Shared |

## What Each Person Built

### Dina (Classifier + Frontend)

- Trained ConvNeXt Tiny on RVL-CDIP in Colab (2 epochs, CPU inference ~0.71 s).
- Selected the 50-image golden set across all 16 classes.
- Exported `classifier.pt`, generated `model_card.json` with SHA-256 and full test metrics.
- Built the React/TypeScript/Vite frontend console: login, dashboard, batches, review queue, demo ingestion guide, RBAC role preview.
- Wired the frontend to the real JWT API (login, batches, predictions, audit log).
- Configured Vite dev proxy and nginx production proxy so the browser never needs CORS headers.
- Wired the frontend into docker-compose as the `frontend` service.

### Jamal (API / Service Architecture)

- Backend architecture and project documentation
- Postgres schema and Alembic migrations
- Layered FastAPI backend structure
- Domain models, repositories, and services
- Worker-facing service write paths
- Prediction idempotency guard
- API read-path endpoints
- FastAPI Users JWT authentication
- Vault-backed JWT configuration
- First-admin bootstrap flow
- Casbin RBAC implementation
- Route permission enforcement
- Role management endpoints
- Last-admin protection
- Audit logging for role changes
- Prediction review/relabel endpoint
- Admin user invite endpoint
- Docker Compose local bootstrap support
- Service-specific dependency split
- Vault-first secret handling
- Unit and route test coverage
### [Teammate 3] (Ingestion + Workers)

- Implemented SFTP polling in `sftp-ingest` (5-second poll interval, 50 MB size limit).
- Validated and quarantined malformed SFTP drops, writing failed batch records.
- Uploaded raw TIFFs to MinIO and enqueued RQ jobs with the agreed payload shape.
- Implemented the inference worker: ConvNeXt forward pass, overlay PNG generation, `record_prediction()` call.
- Propagated request IDs across queue payloads, worker logs, and DB rows.
- Implemented the Vault-backed MinIO and SFTP adapters.

## Merge and Review Process

- Feature branches per component.
- PRs reviewed by at least one teammate before merge.
- Main branch must stay runnable with `docker compose up`.
- PR descriptions include: summary, files changed, test evidence, known limitations.

## Where We Got Stuck and How We Unblocked

The main friction point was the cache invalidation boundary. Early worker drafts were calling cache invalidation directly in the inference path (bypassing the service layer). We caught this in code review — the ARCH.md layer rules were clear enough that the fix was straightforward: the worker calls `prediction_service.record_prediction()`, which owns cache invalidation. The code review process is what caught it before it reached main.

The second friction point was the admin bootstrap flow. The fastapi-users library creates users in the database, but Casbin role assignment is a separate step. We initially documented this as one command but discovered during testing that two separate scripts were needed. We updated the RUNBOOK accordingly.

## A Decision the Team Disagreed On

**Worker writing to the predictions repository directly vs. calling the service layer.**

Initial position: the worker is a background process, not an HTTP handler, so calling the service layer felt like unnecessary indirection. Writing to the repository directly would be faster to implement.

Resolution: we chose the service layer. The reason is that prediction writes must also update batch state, write audit entries where applicable, and invalidate the `/batches/{batch_id}` and `/predictions/recent` caches. Doing all of that correctly in the worker's inference loop would have duplicated the same logic that already lives in the service. Using the service layer keeps the worker consistent with the API write path and ensures cache invalidation can never be accidentally skipped.
