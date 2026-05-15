# RUNBOOK.md

Status: Draft operational guide
Last updated: 2026-05-14

## 1. Local Startup

**First-time setup**: this repository uses Git LFS for `classifier.pt`. Before the first build, run:

```bash
git lfs install
git lfs pull
```

If you skip this, the worker container will refuse to start with a SHA-256 mismatch.

Primary startup path (from a fresh clone):

```bash
cp .env.example .env
docker compose up --build
```

Expected behavior:

1. Vault, Postgres, Redis, MinIO, and SFTP start.
2. `migrate` runs Alembic migrations and exits successfully.
3. `api` starts after startup checks pass.
4. `worker` starts after dependencies are healthy and begins listening on `doc-jobs`.
5. `sftp-ingest` starts polling the SFTP drop folder.

Environment note:

- `.env.example` keeps Vault bootstrap, ports, and non-secret settings only.
- App runtime secrets are still loaded from Vault (`load_secrets()`), never from `.env`.
- Bootstrap credentials for Postgres/MinIO/SFTP rely on Compose dev-only fallbacks unless you override them locally.

If the API refuses to start, check:

- Vault is reachable.
- Vault contains required secrets.
- Casbin policy table is seeded.
- classifier model files exist.
- SHA-256 in `model_card.json` matches `classifier.pt`.
- `test_top1` is above the README threshold.

## 2. Bootstrap First Admin User

Temporary procedure to confirm during implementation.

Expected options:

### Option A: Bootstrap script

```bash
docker compose exec api uv run python backend/scripts/create_admin.py --email admin@example.com
```

### Option B: Public registration followed by role seed

1. Register user through `/auth/register`.
2. Run a seed script or migration that assigns the first admin role.
3. Confirm `/me` returns role `admin`.

Final choice should be documented after auth implementation.

## 3. Drop a TIFF Through SFTP

Temporary manual demo flow:

```bash
scp -P 2222 sample.tif sftp-user@localhost:/upload/
```

Then verify:

1. `sftp-ingest` logs file detected.
2. Raw file appears in MinIO.
3. Redis/RQ job is created.
4. `worker` logs inference completed.
5. Prediction row appears in Postgres.
6. `GET /batches/{batch_id}` shows the prediction.

## 4. Recover a Stuck Queue

Use this when predictions are not appearing after files are dropped.

Checklist:

1. Check Redis is running.
2. Check RQ worker logs.
3. Check whether the job is queued, started, failed, or missing.
4. Check MinIO object exists for the raw TIFF.
5. Check classifier startup checks passed.
6. Requeue failed jobs if the failure was transient.
7. Move malformed files to quarantine if input is invalid.

Commands to fill after RQ is implemented:

```bash
docker compose logs worker
docker compose logs redis
docker compose exec worker uv run python backend/scripts/inspect_queue.py
```

## 5. Replace the Classifier Model

Procedure:

1. Add the new `classifier.pt` through Git LFS.
2. Generate a new `model_card.json`.
3. Compute and store the correct SHA-256.
4. Update full-test and golden-set metrics.
5. Run the golden-set replay test.
6. Restart `api` and `worker`.
7. Confirm startup checks pass.
8. Run a smoke test with one TIFF drop.

Do not replace the model without updating `model_card.json`.

## 6. Vault Failure Recovery

If API fails because Vault is unreachable:

1. Check Vault container logs.
2. Confirm `VAULT_ADDR` and `VAULT_TOKEN` in `.env`.
3. Confirm Vault dev server is initialized/unsealed as expected.
4. Confirm expected KV paths exist.
5. Restart API after Vault is healthy.

```bash
docker compose logs vault
docker compose restart api
```

## 7. Casbin Policy Failure Recovery

If API refuses to start because the Casbin policy table is empty:

1. Confirm migrations ran.
2. Run the Casbin seed script or migration.
3. Confirm policies exist in the database.
4. Restart API.

Expected initial policy includes:

- admin permissions
- reviewer permissions
- auditor permissions

## 8. Cache Debugging

If API reads show stale data:

1. Confirm write operation went through the service layer.
2. Check that service method invalidated the correct cache key.
3. Check Redis connection.
4. Compare DB row vs API response.
5. Temporarily clear Redis cache and retest.

Important rule: routers and repositories do not invalidate cache.

## 9. Health Checks

Planned health endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Basic API process health. |
| `GET /readyz` | Readiness check for DB, Redis, Vault, and required startup dependencies. |

Expected statuses:

- `200 OK`: service is healthy/ready.
- `503 Service Unavailable`: dependency missing or not ready.

## 10. Demo Checklist

Before Friday demo:

- clean clone startup works
- `docker compose up --build` works
- SFTP TIFF becomes visible in API
- admin role toggle works
- reviewer relabel works only below confidence threshold
- auditor cannot mutate anything
- Vault failure causes API restart failure
- broken model hash causes startup failure
- golden-set test fails on deliberately changed expected output
- structured logs include request IDs
