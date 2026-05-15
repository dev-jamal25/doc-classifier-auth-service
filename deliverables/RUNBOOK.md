# RUNBOOK.md

Operational guide for the document classifier service.

## 1. Local Startup

**First-time setup** — the repository uses Git LFS for `classifier.pt`. Before the first build:

```bash
git lfs install
git lfs pull
```

If you skip this the worker refuses to start with a SHA-256 mismatch error.

**Start the full stack:**

```bash
cp .env.example .env
docker compose up --build
```

Expected startup order:

1. `vault` starts in dev mode.
2. `vault-init` seeds Vault KV paths with dev secrets and exits.
3. `db`, `redis`, `minio`, `sftp` start.
4. `minio-init` creates the required MinIO buckets and exits.
5. `migrate` runs `alembic upgrade head` and exits.
6. `api`, `worker`, `sftp-ingest`, `frontend` start.

**Access points:**

| Service | URL |
|---|---|
| Frontend console | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 (minioadmin / minioadmin) |
| Vault UI | http://localhost:8200 (token: dev-only-root-token) |
| SFTP | localhost:2222 |

**If the API refuses to start, check:**

- Vault is reachable and `vault-init` completed successfully.
- `migrate` completed successfully.
- `classifier.pt` exists and its SHA-256 matches `model_card.json`.
- `test_top1` in `model_card.json` is ≥ 0.70.
- Casbin policy table is not empty.

```bash
docker compose logs vault-init
docker compose logs migrate
docker compose logs api
```

## 2. Bootstrap the First Admin User

Two scripts must be run in order after the first `docker compose up`.

**Step 1 — create the user in the database:**

```bash
docker compose exec api uv run python -m app.entrypoints.bootstrap_admin \
  --email admin@example.com --password YourPassword123!
```

**Step 2 — assign the admin Casbin role:**

```bash
docker compose exec api uv run python -m app.entrypoints.bootstrap_admin_role \
  --email admin@example.com
```

Both steps are required. Step 1 creates the user record. Step 2 assigns the Casbin grouping policy that gives the user admin permissions.

**Verify:**

```bash
# Get a JWT token
curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=YourPassword123!" | python -m json.tool

# Check /me shows roles: ["admin"]
TOKEN="<paste access_token here>"
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/me | python -m json.tool
```

On Windows PowerShell:

```powershell
$body = "username=admin@example.com&password=YourPassword123!"
$resp = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -Body $body -ContentType "application/x-www-form-urlencoded"
$token = $resp.access_token
Invoke-RestMethod -Uri http://localhost:8000/me -Headers @{ Authorization = "Bearer $token" }
```

## 3. Drop a TIFF Through SFTP

Default SFTP credentials (dev only, sourced from Vault):

- Host: `localhost`
- Port: `2222`
- Username: `sftp-user`
- Password: `dev-sftp-password`

**Drop a file:**

```bash
sftp -P 2222 sftp-user@localhost
sftp> cd upload
sftp> put sample-document.tiff
sftp> bye
```

Or with scp:

```bash
scp -P 2222 sample-document.tiff sftp-user@localhost:/upload/
```

**Verify the pipeline:**

```bash
# 1. sftp-ingest picks up the file (within 5 seconds)
docker compose logs sftp-ingest --tail 20

# 2. Worker classifies it
docker compose logs worker --tail 20

# 3. Batch appears in the API
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/batches | python -m json.tool

# 4. Check the frontend at http://localhost:3000/batches
```

## 4. Invite Additional Users

Admin invite (requires an admin JWT token):

```bash
curl -s -X POST http://localhost:8000/admin/users/invite \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "reviewer@example.com", "temporary_password": "TempPass123!"}'
```

Then assign a role:

```bash
curl -s -X PUT \
  http://localhost:8000/admin/users/<user_id>/roles/reviewer \
  -H "Authorization: Bearer $TOKEN"
```

## 5. Manage Roles

**Assign a role:**

```bash
curl -s -X PUT \
  http://localhost:8000/admin/users/<user_id>/roles/<role> \
  -H "Authorization: Bearer $TOKEN"
```

**Remove a role:**

```bash
curl -s -X DELETE \
  http://localhost:8000/admin/users/<user_id>/roles/<role> \
  -H "Authorization: Bearer $TOKEN"
```

Valid roles: `admin`, `reviewer`, `auditor`.

The last admin cannot be demoted. The endpoint returns `409 Conflict` if you attempt it.

Every role change writes an audit log entry visible at `GET /admin/audit-log`.

## 6. Recover a Stuck Queue

Use this when predictions are not appearing after files are dropped.

```bash
# Check logs
docker compose logs worker --tail 50
docker compose logs sftp-ingest --tail 50
docker compose logs redis --tail 20

# Confirm MinIO received the raw file
docker compose exec minio mc ls local/documents-raw/

# Confirm Redis queue has jobs
docker compose exec redis redis-cli llen rq:queue:doc-jobs
```

If jobs are stuck in a failed state, restart the worker:

```bash
docker compose restart worker
```

If the SFTP file was malformed, it will appear as a `state: failed` batch in `GET /batches` with a `failure_reason`.

## 7. Replace the Classifier Model

1. Commit the new `classifier.pt` through Git LFS.
2. Update `model_card.json` with the new SHA-256 and metrics.
3. Run the golden-set replay test:
   ```bash
   docker compose exec worker uv run pytest backend/app/classifier/eval/golden.py -v
   ```
4. Restart `api` and `worker`:
   ```bash
   docker compose restart api worker
   ```
5. Confirm startup checks pass in logs.
6. Drop one test TIFF and confirm a prediction appears.

Do not replace `classifier.pt` without updating `model_card.json`. The SHA-256 mismatch will cause both services to refuse to start.

## 8. Vault Failure Recovery

If the API refuses to start because Vault is unreachable:

```bash
docker compose logs vault
docker compose logs vault-init
```

Check that `VAULT_ADDR` and `VAULT_TOKEN` in `.env` are correct, then restart:

```bash
docker compose restart vault vault-init
docker compose restart api
```

To inspect Vault secrets directly (dev mode):

```bash
docker compose exec vault vault kv get \
  -address=http://127.0.0.1:8200 \
  -token=dev-only-root-token \
  secret/doc-classifier/jwt
```

## 9. Cache Debugging

If API reads appear stale after a write:

1. Confirm the write went through the service layer (not a direct repository call).
2. Check that the service method called cache invalidation.
3. Flush Redis and retry:
   ```bash
   docker compose exec redis redis-cli FLUSHDB
   ```
4. Compare DB row vs API response.

Rule: cache invalidation lives only in `app/services/`. Routers and repositories never invalidate.

## 10. Health Check

```bash
curl http://localhost:8000/healthz
```

Returns `200 OK` when the API process is running.

## 11. Demo Checklist

Run through this before the Friday presentation:

- [ ] `git lfs pull` confirms `classifier.pt` is present
- [ ] `cp .env.example .env && docker compose up --build` completes cleanly
- [ ] Bootstrap admin (both scripts) runs successfully
- [ ] `/me` returns `roles: ["admin"]`
- [ ] Frontend at http://localhost:3000 loads and login works
- [ ] SFTP drop → batch appears in frontend within 10 seconds
- [ ] Prediction shows correct label and confidence
- [ ] Admin can toggle a user's role; `/me` for that user reflects the change
- [ ] Reviewer can relabel a prediction with confidence < 0.70
- [ ] Auditor cannot relabel (gets 403)
- [ ] `docker compose stop vault && docker compose restart api` — API fails to start
- [ ] Audit log shows role changes and relabels
- [ ] `docker compose logs api` shows structured JSON with `request_id`
