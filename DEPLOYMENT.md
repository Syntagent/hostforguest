# Deployment

This repo contains a FastAPI API, a Next.js frontend, PostgreSQL/PostGIS with pgvector, and Neo4j.

## Repository Safety

Before pushing to GitHub:

```bash
git status --short
git diff --stat
git ls-files .env "*.db" logs node_modules venv frontend/.next
```

Expected result: `.env`, local SQLite databases, logs, virtualenvs, build output, and `node_modules` are not tracked.

## Required Server Configuration

Create `.env` from `env.example` on the target server and set production values:

```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<random-strong-secret>
POSTGRES_PASSWORD=<random-strong-password>
POSTGRES_HOST_AUTH_METHOD=md5
NEO4J_PASSWORD=<random-strong-password>
NEXT_PUBLIC_API_URL=https://<api-domain>
CORS_ORIGINS=https://<frontend-domain>
GOOGLE_MAPS_API_KEY=
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
VITE_GOOGLE_MAPS_API_KEY=
BOOKING_COM_MOCK=true
DEV_LOGIN_SEED_ENABLED=false
DEV_LOGIN_SEED_FORCE=false
CHANNEL_WEBHOOK_SECRET=
CHANNEL_ENCRYPTION_KEY=
```

Do not commit `.env` or any real API keys.

## Local Development

Follow `AGENTS.md`: run API and UI on the host, not in Docker.

```bash
npm install
npm install --prefix frontend
docker compose up -d postgres neo4j
npm run dev
```

UI: `http://127.0.0.1:3055`
API docs: `http://127.0.0.1:8000/api/v1/docs`

## Docker Server Smoke Test

For a simple server deployment behind a reverse proxy:

```bash
cp env.example .env
# edit .env first
docker compose --profile docker-api up -d --build
docker compose ps
```

Smoke checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/docs
```

Expose the frontend container port through your reverse proxy. By default the host port is `3001`; set `FRONTEND_PUBLISH_PORT=3000` if needed.

## GitHub Push

This repo is published at `https://github.com/Syntagent/hostforguest`. To publish future changes:

```bash
git status --short
git add <changed-files>
git commit -m "<clear change summary>"
git push origin main
```
