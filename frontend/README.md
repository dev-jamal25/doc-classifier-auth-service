# Frontend Console

React/TypeScript/Vite console for the document classifier service.

## Stack

- Vite 5 + React 18 + TypeScript
- Tailwind CSS
- react-router-dom
- lucide-react
- framer-motion

## Local Development

Requires the backend stack running (`docker compose up` from the repo root).

```bash
npm install
npm run dev
```

Opens at http://localhost:5173. Vite proxies `/auth`, `/me`, `/batches`, `/predictions`, `/admin` to the API at `localhost:8000` — no CORS setup needed.

**Windows / Nodist note:** if npm fails to resolve Node, run once in the current PowerShell session:

```powershell
$env:NODIST_X64 = "0"
npm install
npm run dev
```

## Production (Docker)

The full stack including the frontend runs with:

```bash
docker compose up --build
```

Frontend at http://localhost:3000. nginx proxies API paths to the `api` service internally.

## Pages

| Route | Description |
|---|---|
| `/login` | JWT login — calls the real `/auth/login` API |
| `/dashboard` | Batch queue, prediction review panel, audit timeline, role summary |
| `/batches` | Live batch list from `/batches` |
| `/batches/:id` | Batch detail with predictions |
| `/predictions/review` | Low-confidence prediction queue (< 0.70) |
| `/demo-ingestion` | SFTP ingestion walkthrough for the demo |

## API Integration

Login calls `POST /auth/login` (form-encoded), stores the JWT, and fetches `/me` for user profile and roles. All subsequent requests attach `Authorization: Bearer <token>`.

Every page starts with curated mock data for instant render, then replaces it with real API data once the fetch resolves. If the API is unreachable the page remains functional with the mock data.
