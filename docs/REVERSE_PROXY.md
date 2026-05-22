# Reverse proxy for HostForGuest

HostForGuest serves a **Next.js UI** and a **FastAPI API** (`/api/v1/*`, docs at `/api/v1/docs`). In production the browser should call the API on the **same public origin** (path `/api`) so cookies and CORS stay simple.

## Choose an edge

| Approach | When to use | Config in this repo |
|----------|-------------|---------------------|
| **Cloudflare Tunnel** | VPS with no public ports (this project’s default) | [`cloudflared-ingress.example.yml`](../cloudflared-ingress.example.yml), [`docs/VPS_CLOUDFLARE.md`](VPS_CLOUDFLARE.md) |
| **nginx** | Your own TLS on the server, or behind another LB | [`deploy/nginx/hostforguest.conf.example`](../deploy/nginx/hostforguest.conf.example) |
| **Caddy** | Automatic HTTPS with minimal config | [`deploy/caddy/Caddyfile.example`](../deploy/caddy/Caddyfile.example) |

Do **not** expose PostgreSQL through any proxy. Databases bind to `127.0.0.1` only (see `docker-compose.vps-prod.yml`).

## URL and environment contract

For a **single hostname** (recommended):

```env
NEXT_PUBLIC_API_URL=https://<your-domain>
CORS_ORIGINS=https://<your-domain>
```

The UI calls `https://<your-domain>/api/v1/...`. The reverse proxy must forward **`/api`** (and optionally **`/health`**) to the API upstream and everything else to the Next.js upstream.

| Stack | API upstream | UI upstream |
|-------|--------------|-------------|
| VPS prod (`docker-compose.vps-prod.yml`) | `127.0.0.1:8006` | `127.0.0.1:3007` |
| Default Docker (`--profile docker-api`) | `127.0.0.1:8000` | `127.0.0.1:3001` (or `FRONTEND_PUBLISH_PORT`) |
| Local dev (not proxied) | `127.0.0.1:8000` | `127.0.0.1:3055` (Next dev rewrites `/api` in development only) |

After changing `NEXT_PUBLIC_API_URL`, **rebuild** the frontend image (`docker compose ... --build`) so the client bundle picks up the public API base URL.

## Cloudflare Tunnel (VPS layout)

Ingress order matters: **`/api` before the catch-all host**.

Production (`hostforguest.syntagent.com`):

- Path `/api` → `http://127.0.0.1:8006`
- Catch-all → `http://127.0.0.1:3007`

Development (`hostforguest-dev.syntagent.com`):

- Catch-all → `http://127.0.0.1:3055` (Next dev proxies `/api` to `API_PROXY_TARGET`)

Full port map and commands: **[VPS_CLOUDFLARE.md](VPS_CLOUDFLARE.md)**.

## nginx

1. Start the app stack (prod example):

   ```bash
   docker compose -p hostforguest-prod \
     -f docker-compose.yml -f docker-compose.vps-prod.yml \
     --profile docker-api up -d --build
   ```

2. Copy and edit the example:

   ```bash
   sudo cp deploy/nginx/hostforguest.conf.example /etc/nginx/sites-available/hostforguest.conf
   # set server_name and upstream ports (8006 / 3007 for VPS prod)
   sudo ln -sf /etc/nginx/sites-available/hostforguest.conf /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```

3. Enable TLS (optional):

   ```bash
   sudo certbot --nginx -d hostforguest.example.com
   ```

Smoke checks through the proxy:

```bash
curl -fsS https://hostforguest.example.com/health
curl -fsS -o /dev/null -w "%{http_code}\n" https://hostforguest.example.com/api/v1/docs
curl -fsS -o /dev/null -w "%{http_code}\n" https://hostforguest.example.com/
```

## Caddy

1. Adjust hostnames and ports in [`deploy/caddy/Caddyfile.example`](../deploy/caddy/Caddyfile.example).
2. Install the snippet under `/etc/caddy/Caddyfile.d/` (Debian/Ubuntu) or merge into your main `Caddyfile`.
3. Reload: `sudo systemctl reload caddy`

Caddy requests certificates automatically when DNS points at the server and ports 80/443 are reachable.

## Split hostnames (optional)

If you prefer `api.example.com` and `app.example.com`:

```env
NEXT_PUBLIC_API_URL=https://api.example.com
CORS_ORIGINS=https://app.example.com
```

Point `api.example.com` only at the FastAPI upstream; point `app.example.com` only at Next.js. You do not need a path-based `/api` rule on the app hostname.

## Rate limiting and scale

In-app rate limits are relaxed under pytest and can be disabled with `DISABLE_RATE_LIMIT=1` on a single instance. For multiple API replicas, enforce limits at the **edge** (Cloudflare, nginx `limit_req`, or a shared store). See **[RATE_LIMITING.md](RATE_LIMITING.md)**.

## Database migrations on existing deployments

New databases are bootstrapped by `init-db/` and SQLAlchemy `create_all` in the app. **Existing** production databases may need ordered SQL under `migrations/`:

1. List order: `migrations/MIGRATION_ORDER.txt`
2. Apply each file once against the target DB (idempotent scripts are preferred; review each file before re-running).

Example (prod Postgres on localhost `5439`):

```bash
export PGPASSWORD='…'
for f in $(grep -v '^#' migrations/MIGRATION_ORDER.txt | grep -v '^$'); do
  echo "Applying $f"
  psql -h 127.0.0.1 -p 5439 -U tourist_guide_user -d tourist_guide_db -f "migrations/$f"
done
```

Take a backup before applying migrations on production data.

## Related docs

- [DEPLOYMENT.md](../DEPLOYMENT.md) — env checklist and Docker smoke test
- [VPS_CLOUDFLARE.md](VPS_CLOUDFLARE.md) — tunnel hostnames and ports on this server
