# Document Classifier — Authenticated Service

An internal document classification service for the SE Factory AIE Bootcamp, Week 6.

A scanner vendor drops grayscale TIFF documents into SFTP. An ingestion pipeline stores the files, queues classification jobs, and an inference worker classifies each document against the 16 RVL-CDIP layout classes. Authenticated users browse batches, review predictions, and relabel low-confidence results through a permission-gated API and React console.

## Quick Start

```bash
git lfs install
git lfs pull
cp .env.example .env
docker compose up --build
```

The stack starts in dependency order. `migrate` runs Alembic migrations and exits before `api` boots. All secrets are seeded into Vault automatically by `vault-init`.

**Bootstrap the first admin user** (run once after first `docker compose up`):

```bash
docker compose exec api uv run python -m app.entrypoints.bootstrap_admin \
  --email admin@example.com --password YourPassword123!

docker compose exec api uv run python -m app.entrypoints.bootstrap_admin_role \
  --email admin@example.com
```

Both scripts are required. The first creates the user. The second assigns the Casbin admin role.

**Access the console:**

| Interface | URL |
|---|---|
| Frontend console | http://localhost:3000 |
| API (Swagger) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| Vault UI | http://localhost:8200 |

## Services

| Service | Purpose |
|---|---|
| `api` | FastAPI app — auth, RBAC, batch browsing, prediction review, audit log |
| `worker` | RQ inference worker — consumes jobs, runs ConvNeXt, writes predictions |
| `sftp-ingest` | Polls SFTP, uploads TIFFs to MinIO, enqueues classification jobs |
| `migrate` | Runs `alembic upgrade head` and exits before `api` starts |
| `db` | Postgres 16 |
| `redis` | Redis 7 — RQ queue and fastapi-cache2 backend |
| `minio` | S3-compatible blob storage for raw TIFFs and overlay PNGs |
| `sftp` | atmoz/sftp SFTP drop target |
| `vault` | HashiCorp Vault dev mode for secret resolution |
| `frontend` | React/Vite console served by nginx on port 3000 |

## Drop a Test Document

```bash
sftp -P 2222 sftp-user@localhost
sftp> cd upload
sftp> put sample-document.tiff
sftp> bye
```

The file should appear as a batch in the console at http://localhost:3000/batches within 10 seconds.

## Classifier Model

| Field | Value |
|---|---|
| Backbone | `convnext_tiny` |
| Weights | `ConvNeXt_Tiny_Weights.DEFAULT` |
| Freeze policy | `partial_unfreeze_final_stage_and_classifier` |
| Test top-1 | **0.8029** (39 999 / 40 000 examples) |
| Test top-5 | **0.9635** |
| Worst class | `scientific_report` — 0.516 |
| Best class | `file_folder` — 0.958 |
| SHA-256 | `c5c862ea4213ace93aaafb17e4fd9413c17ad1bdc91e9ec74b4cd15b21fe48c0` |
| Min startup threshold | test top-1 ≥ 0.70 |

The API and worker refuse to start if the SHA-256 does not match `model_card.json` or if `test_top1` is below the threshold above.

## Latency Budgets

Measured on CPU, ConvNeXt Tiny, single-document batch, local docker-compose.

| Metric | Budget | Basis |
|---|---|---|
| API cached reads p95 | < 50 ms | Redis response time |
| API uncached reads p95 | < 200 ms | Postgres + serialization |
| Inference per document p95 | < 1.0 s | ConvNeXt Tiny CPU (observed: ~0.71 s) |
| End-to-end SFTP drop → visible in API p95 | < 10 s | Full pipeline with 5 s poll interval |

## Roles

| Role | Can Do |
|---|---|
| `admin` | Invite users, toggle roles, view audit log, view batches |
| `reviewer` | View batches, relabel predictions where top-1 confidence < 0.70 |
| `auditor` | Read-only access to batches and audit log |

## Documentation

| Document | Contents |
|---|---|
| [ARCH.md](deliverables/ARCH.md) | System architecture, layer boundaries, data flow, caching plan |
| [DECISIONS.md](deliverables/DECISIONS.md) | Architecture decision records |
| [RUNBOOK.md](deliverables/RUNBOOK.md) | Startup, bootstrap, SFTP demo, failure recovery |
| [SECURITY.md](deliverables/SECURITY.md) | Secret handling, auth, audit log, startup checks |
| [COLLABORATION.md](deliverables/COLLABORATION.md) | Team ownership, Trello board, merge process |
| [LICENSES.md](deliverables/LICENSES.md) | Dataset and dependency licenses |
