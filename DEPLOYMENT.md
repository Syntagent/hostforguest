# Deployment

This repo contains a FastAPI API, a Next.js frontend, and PostgreSQL/PostGIS with pgvector.

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
docker compose up -d postgres
npm run dev
```

UI: `http://127.0.0.1:3055`
API docs: `http://127.0.0.1:8000/api/v1/docs`

## VPS (this server) — Cloudflare Tunnel only

See **[docs/VPS_CLOUDFLARE.md](docs/VPS_CLOUDFLARE.md)** for hostnames, ports, and tunnel ingress.

| Hostname | Cloudflare → |
|----------|----------------|
| `hostforguest.syntagent.com` | UI `127.0.0.1:3007`, `/api` → `127.0.0.1:8006` |
| `hostforguest-dev.syntagent.com` | `127.0.0.1:3055` |

## Reverse proxy

For nginx, Caddy, path-based routing (`/api` → API, `/` → UI), port maps, and migration notes on existing databases, see **[docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md)** and **`deploy/nginx/`** / **`deploy/caddy/`** examples.

On this VPS, public access uses **Cloudflare Tunnel** only — see **[docs/VPS_CLOUDFLARE.md](docs/VPS_CLOUDFLARE.md)**.

## Reverse proxy (nginx / Caddy / Cloudflare)

See **[docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md)** for path routing, port maps, migration apply loop, and smoke checks. Example configs: [`deploy/nginx/hostforguest.conf.example`](deploy/nginx/hostforguest.conf.example), [`deploy/caddy/Caddyfile.example`](deploy/caddy/Caddyfile.example). Tunnel ingress: [`cloudflared-ingress.example.yml`](cloudflared-ingress.example.yml), [`docs/VPS_CLOUDFLARE.md`](docs/VPS_CLOUDFLARE.md).

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
