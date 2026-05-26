# HostForGuest on VPS — Cloudflare only

Public access is **only** via Cloudflare Tunnel (no HAProxy). DNS hostnames route to **localhost** ports on this server.

## Hostnames

| Hostname | Stack | Purpose |
|----------|--------|---------|
| `hostforguest.syntagent.com` | **Production** (Docker) | Live app |
| `hostforguest-dev.syntagent.com` | **Development** (host API + UI, Docker DB only) | Staging / dev |

No other public hostnames are required for the main app. Optional later: `api.hostforguest.syntagent.com` (not used in this layout).

## Ports to wire in Cloudflare Tunnel

Add these **ingress** rules in [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → your tunnel → **Public Hostname** (most specific paths first).

### Production — `hostforguest.syntagent.com`

| Tunnel rule | Origin service |
|-------------|----------------|
| `hostforguest.syntagent.com` + path `/api` | `http://127.0.0.1:8006` |
| `hostforguest.syntagent.com` (catch-all) | `http://127.0.0.1:3007` |

### Development — `hostforguest-dev.syntagent.com`

| Tunnel rule | Origin service |
|-------------|----------------|
| `hostforguest-dev.syntagent.com` (catch-all only) | `http://127.0.0.1:3055` |

Dev API runs on `127.0.0.1:8010`. Next.js **dev** rewrites `/api/*` → `API_PROXY_TARGET` (see `env.vps-dev.example`). You do **not** need a separate tunnel rule for `/api` on the dev hostname unless you stop using `npm run dev`.

Copy-paste ingress block: [`cloudflared-ingress.example.yml`](../cloudflared-ingress.example.yml).

## Port map (this VPS)

| Service | Environment | Bind address | Notes |
|---------|-------------|--------------|--------|
| PostgreSQL | Dev | `127.0.0.1:5440` | Docker only (`docker compose … vps-dev`; 5434 reserved by matchmakingrcc) |
| PostgreSQL | Prod | `127.0.0.1:5439` | Docker only (`docker compose … vps-prod`) |
| FastAPI | Dev | `127.0.0.1:8010` | Host: `npm run dev:api:8010` |
| Next.js | Dev | `127.0.0.1:3055` | Host: `npm run dev:frontend` |
| FastAPI | Prod | `127.0.0.1:8006` | Docker `api` (internal 8000) |
| Next.js | Prod | `127.0.0.1:3007` | Docker `frontend` (internal 3000) |

Databases are **not** exposed to Cloudflare.

## Directory layout

| Path | Role |
|------|------|
| `/home/bperak/development/hostforguest` | Dev codebase; host API/UI; Docker DB |
| `/home/bperak/production/hostforguest` | Prod codebase; full Docker stack |

## Environment URLs

**Production** (`.env` in `production/hostforguest`):

```env
ENVIRONMENT=production
NEXT_PUBLIC_API_URL=https://hostforguest.syntagent.com
CORS_ORIGINS=https://hostforguest.syntagent.com
```

**Development** (`.env` in `development/hostforguest`):

```env
ENVIRONMENT=development
POSTGRES_PORT=5440
API_PROXY_TARGET=http://127.0.0.1:8010
# Leave NEXT_PUBLIC_API_URL empty so the browser uses same-origin /api (Next rewrite).
CORS_ORIGINS=https://hostforguest-dev.syntagent.com,http://127.0.0.1:3055
```

## Commands

### Development

```bash
cd /home/bperak/development/hostforguest
cp env.vps-dev.example .env   # once; then edit secrets
docker compose -p hostforguest-dev -f docker-compose.yml -f docker-compose.vps-dev.yml up -d postgres
npm install && npm install --prefix frontend
npm run dev:8010   # API :8010 + UI :3055
```

### Production

```bash
cd /home/bperak/production/hostforguest
cp env.vps-prod.example .env   # once; set SECRET_KEY, POSTGRES_PASSWORD, API keys
docker compose -p hostforguest-prod \
  -f docker-compose.yml -f docker-compose.vps-prod.yml \
  --profile docker-api up -d --build
curl -sS http://127.0.0.1:8006/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3007/
```

After changing tunnel hostnames in Cloudflare, no server reload is needed beyond ensuring processes listen on the ports above.

## Deploy flow

1. Develop in `development/hostforguest` → push to GitHub.
2. In `production/hostforguest`: `git pull` → rebuild Docker stack.
3. Confirm tunnel hostnames still point at **8006** and **3007** (prod) or **3055** (dev).

See also: [`DEPLOYMENT.md`](../DEPLOYMENT.md), [`/home/bperak/development/DOCKER_PORT_DISTRIBUTION.md`](../../DOCKER_PORT_DISTRIBUTION.md).
