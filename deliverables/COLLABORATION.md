# COLLABORATION.md

Status: Draft collaboration plan
Last updated: 2026-05-12

## Trello Board

Trello: `TODO: paste Trello board link here`

The Trello board is the visible record of how the team split, reviewed, and shipped the work. Cards should move through:

```text
To Do -> In Progress -> Review -> Done
```

## Team Ownership

Current working split to confirm:

| Area | Owner | Notes |
|---|---|---|
| Classifier / Colab training | Teammate 1 | Fine-tune ConvNeXt Tiny/Small, full test evaluation, model card, SHA-256, golden set. |
| API / service architecture | Jamal | FastAPI routes, layered backend, auth, RBAC, services/repositories, cache invalidation, audit log, startup checks, docs. |
| Ingestion + inference workers | Teammate 2 | SFTP polling, MinIO upload, Redis/RQ enqueueing, worker inference path, overlay write, worker logs. |
| CI / smoke tests / integration support | TODO if fourth teammate exists, otherwise shared | Golden-set CI, compose smoke test, lint/type-check, integration support. |

If the group is officially three people, CI and smoke testing should be shared and assigned as explicit Trello cards so the board does not look like one person carried all cross-cutting work.

## Planned Work Breakdown

### Classifier Owner

- Train ConvNeXt on RVL-CDIP in Colab.
- Select 50-image golden set.
- Export `classifier.pt`.
- Generate `model_card.json`.
- Provide SHA-256 and full-test metrics.
- Implement or support golden-set replay test.

### Service/API Owner

- Define DB schema and Alembic migrations.
- Implement layered API structure.
- Implement fastapi-users JWT auth.
- Implement Casbin RBAC.
- Implement batch/prediction/audit endpoints.
- Implement service-layer cache invalidation.
- Implement Vault startup secret resolution.
- Implement refuse-to-start checks.
- Maintain `ARCH.md`, `DECISIONS.md`, `SECURITY.md`, and `RUNBOOK.md`.

### Ingestion/Worker Owner

- Implement SFTP polling.
- Upload raw files to MinIO.
- Enqueue RQ jobs.
- Run classifier inference in worker.
- Write overlay PNGs to MinIO.
- Call `prediction_service.record_prediction(...)`.
- Propagate request IDs across queue and logs.

### Shared Responsibilities

- Docker Compose integration.
- CI pipeline.
- Smoke test from SFTP drop to API prediction.
- Presentation script.
- Code review of each other's components.

## Merge and Review Process

Proposed workflow:

1. Work on feature branches.
2. Open small PRs by component.
3. At least one teammate reviews before merge.
4. PR description includes:
   - summary
   - files changed
   - test evidence
   - known limitations
5. Main branch must stay runnable with `docker compose up`.

Suggested branch examples:

```text
feature/api-layer-skeleton
feature/auth-rbac
feature/ingestion-worker
feature/classifier-artifacts
feature/cache-audit-log
test/sftp-smoke-test
docs/architecture-baseline
```

## Integration Contracts

The team must agree on these before parallel implementation:

1. Database schema.
2. `prediction_service.record_prediction(...)` signature.
3. `model_card.json` schema.
4. Request ID field name and format.
5. MinIO bucket names and blob key format.
6. Queue payload shape.
7. Casbin role names.

## Where We Expect Friction

Potential risks:

- Service layer must be ready early because the worker depends on it.
- Classifier artifact format must be stable before startup checks and CI are finalized.
- Cache invalidation is easy to accidentally put in the router or repository, which would violate the architecture.
- Three-person split means cross-cutting tasks like CI and docs must be explicit Trello cards, not hidden work.

## Disagreement / Decision Log

Temporary example to replace with real team discussion:

> We initially debated whether the worker should write directly to the predictions repository or call the service layer. We chose the service layer because prediction writes must also update batch state, create audit/cache effects where needed, and invalidate cached API reads. This keeps the worker consistent with the API write path.

Add at least one real disagreement here before submission.
