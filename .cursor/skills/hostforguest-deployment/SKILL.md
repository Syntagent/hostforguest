---
name: hostforguest-deployment
description: Deploy HostForGuest to production -- Docker Compose, pgvector, Cloudflare Tunnel, maintenance cron. Use when deploying, troubleshooting the stack, or fixing database issues.
---

# HostForGuest -- Deployment Guide

## Architecture

- **Backend:** FastAPI on port **8000** (container) exposed on host port **8000**
- **Frontend:** Next.js on port **3001** (container) exposed on host port **3055**
- **Database:** PostgreSQL + pgvector on **5434** (host)
- **Stack:** FastAPI + Next.js + PostgreSQL/pgvector + Docker Compose

## Deploy Steps

1. Start the stack:
   cd /home/bperak/development/hostforguest
   docker compose -f docker-compose.vps-prod.yml up -d --build

2. Verify:
   curl http://localhost:8000/api/v1/docs
   curl http://localhost:3055

3. Run migrations:
   docker compose exec api alembic upgrade head

## pgvector Extension

PostgreSQL needs pgvector extension. If missing:
   docker compose exec postgres psql -U postgres -d touristguide -c "CREATE EXTENSION IF NOT EXISTS vector;"

See `.cursor/skills/hostforguest-pgvector/SKILL.md` for detailed pgvector troubleshooting.

## Maintenance Cron

Set `MAINTENANCE_JOB_SECRET` in `.env`:
   python scripts/run_maintenance_preventive.py

Or via API:
   POST /api/v1/maintenance/jobs/run-preventive-global
   Header: X-Maintenance-Job-Secret

## Environment

- `NEXT_PUBLIC_API_URL=http://localhost:8000` (local dev)
- `PREFERRED_AI_PROVIDER=google` or `openai`
- `GOOGLE_AI_API_KEY` for Gemini integration
- `OPENAI_API_KEY` for OpenAI integration

## Troubleshooting

- **pgvector not found:** Run CREATE EXTENSION command above.
- **Port conflict:** API uses 8000, frontend 3055. Stop other services on these ports.
- **AI features not working:** Check API key and provider config in `.env`.
