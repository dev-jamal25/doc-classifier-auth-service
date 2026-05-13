# DECISIONS.md

Status: Baseline decisions document
Purpose: Record architecture and implementation decisions as the project evolves.

Each decision should follow this format:

```text
## D-XXX: Decision title

Status: Proposed | Accepted | Rejected | Superseded
Date: YYYY-MM-DD
Owner: Name

### Context
What problem are we solving?

### Decision
What did we decide?

### Why
Why this option?

### Alternatives Considered
- Option A
- Option B

### Trade-offs
What do we gain and what do we accept?
```

---

## D-001: Backend Layer Boundary

Status: Accepted
Date: 2026-05-13
Owner: Service/API owner

### Context

The backend needs to stay easy to review, test, and extend. The Week 6 architecture expects clear separation between HTTP, business logic, SQL, domain models, infrastructure adapters, and ORM models.

### Decision

Use the following backend layers:

- `app/api/`
- `app/services/`
- `app/repositories/`
- `app/domain/`
- `app/infra/`
- `app/db/`

### Why

This keeps responsibilities separated:

- routers handle HTTP only
- services own business rules and cache invalidation
- repositories own SQL
- domain models define internal contracts
- infra adapters talk to external systems
- db models stay isolated from API responses

### Trade-offs

This creates more files early, but makes the codebase easier to defend and easier to extend during the live review.

---

## D-002: Team Size

Status: Accepted
Date: 2026-05-13
Owner: Team

### Context

The project brief expects groups of four, but our working group has three members.

### Decision

Submit as a team of 3 people.

### Why

This reflects the actual team structure and helps us split ownership clearly.

### Trade-offs

Cross-cutting work such as CI, smoke tests, integration fixes, and documentation must be explicitly assigned so it does not silently fall on one person.

---

## D-003: Registration Flow

Status: Accepted
Date: 2026-05-13
Owner: Service/API owner

### Context

The service is an internal authenticated system. Public registration is not the best fit for the project story because users should be controlled by admins.

### Decision

Use admin-invite-only registration.

### Why

This supports the internal-service story and makes the permission model cleaner. Admins control who can access the system.

### Alternatives Considered

- Public registration
- Temporarily public registration for demo speed

### Trade-offs

Admin-invite-only is slightly more work, but it is easier to defend from a security and authorization perspective.

---

## D-004: Role Storage

Status: Accepted
Date: 2026-05-13
Owner: Service/API owner

### Context

The team needed to decide whether roles should be stored as a user table column, a join table, or through Casbin.

### Decision

Use Casbin grouping policy only as the source of truth for roles.

### Why

The project already requires Casbin. Keeping role assignment inside Casbin avoids duplicating role state across multiple tables.

### Alternatives Considered

- `role` column on the users table
- `user_roles` join table
- Casbin grouping policy only

### Trade-offs

This keeps authorization centralized, but any service logic that needs to count admins or check roles must query Casbin grouping policy.

---

## D-005: Model Card Schema

Status: Accepted
Date: 2026-05-13
Owner: Classifier owner + Service/API owner

### Context

The classifier owner has not finalized the exact `model_card.json` fields yet. The API and worker still need a startup validation path.

### Decision

Use a temporary permissive Pydantic schema that validates the known required fields and allows extra fields.

Known required fields for now:

- `sha256`
- `backbone`
- `weights_enum`
- `freeze_policy`
- `test_top1`
- `test_top5`
- `per_class_accuracy`

### Why

This allows the service startup-check code to move forward without blocking on the final classifier model card format.

### Trade-offs

A permissive schema is flexible early, but we should tighten it once the classifier owner finalizes the model card.

---

## D-006: Model Startup Threshold

Status: Accepted
Date: 2026-05-13
Owner: Team

### Context

The API and worker should refuse to start if the committed classifier metric is below the threshold documented in the README.

### Decision

Use this temporary threshold:

```text
test_top1 >= 0.70
```

### Why

This aligns startup validation with the threshold currently carried in
`backend/app/classifier/models/model_card.json`, which is treated as authoritative for this phase.

### Trade-offs

The threshold may need to be adjusted after full Colab evaluation, but fixing it now lets startup validation be implemented.

---

## D-007: Maximum SFTP File Size

Status: Accepted
Date: 2026-05-13
Owner: Ingestion/worker owner

### Context

The ingestion worker needs a clear rule for oversized files so malformed drops do not exhaust local resources.

### Decision

Set the maximum accepted SFTP file size to:

```text
50MB
```

### Why

50MB is large enough for normal TIFF scan files in this project, but small enough to protect the local stack from accidental huge uploads.

### Trade-offs

A valid but unusually large scan may be rejected. The rejected file will still be logged and recorded as a failed batch.

---

## D-008: Malformed SFTP Drops

Status: Accepted
Date: 2026-05-13
Owner: Ingestion/worker owner + Service/API owner

### Context

Malformed SFTP drops should not be ignored silently. The system needs visibility into failed ingestion events.

### Decision

Malformed SFTP drops create failed batch rows in Postgres.

For failed SFTP batches:

```text
source = "sftp-ingest"
created_by_user_id = null
state = "failed"
failure_reason = "<reason>"
```

Examples of failure reasons:

- empty file
- invalid image
- unsupported file type
- file exceeds 50MB
- corrupted TIFF

The ingestion worker should also log the failure and move the file to quarantine when possible.

### Why

Failed ingestion is still a system event. Keeping it in the database makes it visible, auditable, and easier to debug.

### Alternatives Considered

- Only log malformed files
- Create a special system user and link failed batches to it

### Trade-offs

Using `created_by_user_id = null` is simpler than creating a system user. The source field still makes it clear that the failed batch came from the SFTP ingestion pipeline.

---

## D-009: Cache TTLs and Invalidation

Status: Accepted
Date: 2026-05-13
Owner: Service/API owner

### Context

The project requires Redis-backed caching for key read endpoints. The team needs clear TTLs and invalidation rules.

A TTL is the maximum time a cached response can live before Redis expires it automatically. Writes still invalidate the relevant cache keys immediately through the service layer.

### Decision

Use these cache TTLs:

| Cached Endpoint | TTL |
|---|---:|
| `GET /me` | 300s |
| `GET /batches` | 60s |
| `GET /batches/{batch_id}` | 60s |
| `GET /predictions/recent` | 60s |

Invalidation rules:

| Cached Endpoint | Invalidated By |
|---|---|
| `GET /me` | Role change targeting that user |
| `GET /batches` | New batch, batch state change |
| `GET /batches/{batch_id}` | Batch state change, prediction write, relabel |
| `GET /predictions/recent` | New prediction write, relabel |

### Why

Batch and prediction data changes frequently during ingestion, so those endpoints use short TTLs. `/me` changes less often, so it can have a longer TTL while still being invalidated immediately on role changes.

### Trade-offs

Short TTLs reduce stale data risk but provide less caching benefit. This is acceptable for the project because correctness and demo reliability matter more.

---

## D-010: Last Admin Demotion Protection

Status: Accepted
Date: 2026-05-13
Owner: Service/API owner

### Context

The system should not allow the only admin to remove their own admin access.

### Decision

Before demoting an admin, count the current users assigned to the `admin` role through Casbin grouping policy.

If only one admin exists, block the demotion.

### Why

This prevents the system from reaching a state where no user can manage roles.

### Alternatives Considered

- Allow all role changes
- Store `is_admin` in the users table and count from there

### Trade-offs

Because roles are stored in Casbin grouping policy only, the service layer must query Casbin to count admins.

---

## D-011: SFTP-to-API Smoke Test Ownership

Status: Accepted
Date: 2026-05-13
Owner: Infra/worker owner, supported by Service/API owner

### Context

The smoke test proves the system works end to end from SFTP drop to API-visible prediction.

### Decision

The infra/worker owner leads the SFTP-to-API smoke test.

The Service/API owner supports the final API assertion.

Expected flow:

```text
SFTP drop -> sftp-ingest -> MinIO -> Redis/RQ -> worker -> Postgres -> GET /batches/{batch_id}
```

### Why

The smoke test crosses infrastructure, worker logic, storage, queueing, and API reads. The infra/worker owner is closest to most of that path, while the API owner ensures the prediction is visible through the correct endpoint.

### Trade-offs

This is shared integration work, so it should be represented clearly on the Trello board.

---

## D-012: Queue Payload Shape

Status: Accepted
Date: 2026-05-13
Owner: Ingestion/worker owner + Service/API owner

### Context

The SFTP ingestion worker and inference worker need a stable queue contract.

### Decision

Use this queue payload shape:

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

Required fields:

- `batch_id`
- `blob_key`
- `source_filename`
- `sftp_user`
- `request_id`
- `received_at`

### Why

The worker needs `batch_id`, `blob_key`, and `request_id` to process the job and write results. The extra fields improve logging and debugging.

### Trade-offs

The payload includes a few metadata fields the worker may not strictly need for inference, but they help observability and support easier debugging.

---

## Remaining Decisions To Add Later

The following are intentionally not finalized yet:

- Final `model_card.json` schema from the classifier owner
- Whether the smoke test runs fully in CI or partly manual for demo
- Final MinIO bucket names and blob key format
- Final CI responsibilities and test split between teammates
