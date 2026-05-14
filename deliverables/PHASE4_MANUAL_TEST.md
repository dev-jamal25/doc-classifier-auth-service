# PHASE4_MANUAL_TEST.md

Status: Historical manual fallback
Last updated: 2026-05-14

This Phase 4 flow is retained only as a manual fallback reference.

Preferred startup path:

```bash
cp .env.example .env
docker compose up --build
```

If you need the future worker container for Phase 5 testing, opt in explicitly:

```bash
docker compose --profile phase5-worker up --build
```

Use this document only when Compose startup is unavailable or when debugging
a specific legacy/manual step.
