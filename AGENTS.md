# Agent / developer rules — read before running the app

## Non‑negotiable: local development (stop the Docker mess)

1. **Develop on the host.** UI **http://127.0.0.1:3055**, API **http://localhost:8000** (or `127.0.0.1:8000`).
2. **Do not** use Docker `api` / `frontend` for day‑to‑day coding. They steal **8000** / **3001** and you will debug the wrong process.
3. If containers were started: `docker compose stop api frontend` (Postgres/Neo4j can stay up).
4. **`.env`:** `NEXT_PUBLIC_API_URL=http://localhost:8000` — must match the uvicorn port.
5. **Sanity check:** `http://localhost:8000/api/v1/docs` (not `/docs`).

**Commands:** repo root `npm run dev` *or* two terminals: `npm run dev:api` + `npm run dev:frontend`.

Full detail: **`.cursor/rules/touristguide-local-dev.mdc`** (always applied in Cursor).
