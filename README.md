# HostForGuest

HostForGuest is a full-stack platform for Croatian accommodation hosts. Hosts manage guest groups, local attractions, itineraries, maintenance and cleaning workflows, channel integrations, and AI-assisted recommendations. Guests join with an access code and receive a lightweight local guide experience.

For server setup and GitHub distribution steps, see [DEPLOYMENT.md](DEPLOYMENT.md).

## What Is In This Repo

- `app/` - FastAPI backend, SQLAlchemy models, services, scheduled tasks, and API routes.
- `frontend/` - Next.js host and guest UI.
- `support_app/day_planner/` - Vite-based day planner support app.
- `init-db/` and `migrations/` - PostgreSQL bootstrap and migration SQL.
- `tests/` - backend and integration tests.
- `docker-compose.yml` - database services by default, full app containers behind an explicit profile.

## Current Architecture

- API: FastAPI on `127.0.0.1:8000`
- UI: Next.js on `127.0.0.1:3055`
- Database: PostgreSQL/PostGIS with pgvector
- AI providers: OpenAI and Google Gemini through environment or per-host settings
- Real-time source updates: local scraping and Crawl4AI-oriented services, not an external project-management knowledge base

## Local Development

Use host-based development. Do not run the Docker `api` or `frontend` services for day-to-day work because they can shadow the local ports.

```bash
npm install
npm install --prefix frontend
docker compose up -d postgres
npm run dev
```

Open:

- UI: `http://127.0.0.1:3055`
- API health: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/api/v1/docs`

If Docker app containers were started accidentally:

```bash
docker compose stop api frontend
```

## Environment

Copy `env.example` to `.env` and set real values where needed.

Minimum local defaults:

```env
ENVIRONMENT=development
DEBUG=true
USE_POSTGRESQL=true
POSTGRES_SERVER=localhost
POSTGRES_PORT=5434
POSTGRES_USER=tourist_guide_user
POSTGRES_PASSWORD=
POSTGRES_DB=tourist_guide_db
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Production must set a strong `SECRET_KEY`, real database passwords, explicit `CORS_ORIGINS`, and any API keys required for AI, maps, or channel integrations.

## Useful Commands

```bash
npm run dev
npm run dev:api
npm run dev:frontend
npm run check:ports
python -m pytest
python -m compileall -q app
docker compose config --quiet
```

## SQL migrations (incremental)

Incremental DDL is in `migrations/`; order is listed in `migrations/MIGRATION_ORDER.txt`. With Postgres reachable (e.g. Docker on `localhost:5434`) and `psql` on your PATH:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/apply_migrations.ps1
```

Use `-DryRun` to list files only. Set `POSTGRES_PASSWORD` in the environment if required.

Support app:

```bash
npm install --prefix support_app/day_planner
npm run build --prefix support_app/day_planner
```

## API Surface

Main route groups live under `/api/v1`:

- `/hosts`
- `/guest-groups`
- `/attractions`
- `/recommendations`
- `/itineraries`
- `/settings`
- `/maintenance`
- `/cleaning`
- `/partners`
- `/channel-integrations`
- `/channel-webhooks`
- `/realtime`
- `/vector`

## Deployment

For a Docker-based server smoke test:

```bash
cp env.example .env
# edit .env first
docker compose --profile docker-api up -d --build
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/docs
```

Put the API and frontend behind a reverse proxy and configure `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` for the public domains. Example configs: **[docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md)** (`deploy/nginx/`, `deploy/caddy/`, or Cloudflare Tunnel in `cloudflared-ingress.example.yml`).

## Security Notes

- Never commit `.env` or real API keys.
- Rotate any key that was ever committed in local history before public distribution.
- `BOOKING_COM_MOCK=true` is the safe default until production channel credentials are configured.
- Use `POSTGRES_HOST_AUTH_METHOD=md5` or stronger on deployed servers.

## Status

This repository is being prepared for distribution as `Syntagent/hostforguest`. The current code path is local-first and self-contained.
