# Deploy examples

Copy-paste configs for production edges. Full guide: **[docs/REVERSE_PROXY.md](../docs/REVERSE_PROXY.md)**.

| File | Role |
|------|------|
| [nginx/hostforguest.conf.example](nginx/hostforguest.conf.example) | Same-origin TLS + `/api` → FastAPI, `/` → Next.js |
| [caddy/Caddyfile.example](caddy/Caddyfile.example) | Same layout with automatic HTTPS |

Replace `APP_DOMAIN` and upstream ports (`8006` / `3007` for VPS prod; `8000` / `3001` for default Docker) before enabling.
