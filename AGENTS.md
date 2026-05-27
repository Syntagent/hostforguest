# Agent / developer rules — read before running the app

## Non‑negotiable: local development (stop the Docker mess)

1. **Develop on the host.** UI **http://127.0.0.1:3055**, API **http://localhost:8000** (or `127.0.0.1:8000`).
2. **Do not** use Docker `api` / `frontend` for day‑to‑day coding. They steal **8000** / **3001** and you will debug the wrong process.
3. If containers were started: `docker compose stop api frontend` (Postgres can stay up).
4. **`.env`:** `NEXT_PUBLIC_API_URL=http://localhost:8000` — must match the uvicorn port.
5. **Sanity check:** `http://localhost:8000/api/v1/docs` (not `/docs`).

**Commands:** repo root `npm run dev` *or* two terminals: `npm run dev:api` + `npm run dev:frontend`.

Full detail: **`.cursor/rules/touristguide-local-dev.mdc`** (always applied in Cursor).

**Tests:** full `pytest` sets `PYTEST_CURRENT_TEST` so in-app rate limiting is skipped; you can also set `DISABLE_RATE_LIMIT=1`. CI smoke sets **`TOURISTGUIDE_PYTEST=1`** and uses compose Postgres on **`localhost:5434`** (`tests/conftest.py`). Run **`bash scripts/ci-smoke-backend.sh`** or **`bash scripts/run-postgres-regression.sh`** for the full suite. See **`docs/RATE_LIMITING.md`** for production vs multi-instance behavior.

**CI smoke (same list as GitHub Actions):** repo root **`npm run test:ci-smoke`** (Windows) or **`npm run test:ci-smoke:sh`** / **`bash scripts/ci-smoke-backend.sh`** — paths live in **`scripts/ci-smoke-backend.txt`** (edit that file to widen or narrow coverage).

**Preventive maintenance (cron):** set **`MAINTENANCE_JOB_SECRET`** in `.env`, then either run **`python scripts/run_maintenance_preventive.py`** daily, or `POST /api/v1/maintenance/jobs/run-preventive-global` with header **`X-Maintenance-Job-Secret`** (same value). Opens due issues from `maintenance_schedules` for all hosts.

**Adaptation “Analyze (AI)”:** needs a working AI provider. With **`PREFERRED_AI_PROVIDER=google`** (or `both`), **`GOOGLE_AI_API_KEY`** enables Gemini (structured JSON + optional before-photo **vision** when you add public **HTTPS** image URLs). With **`openai`**, use **`OPENAI_API_KEY`** — same vision path via OpenAI **`json_object`** + image attachments. Indicative only; not a quote.

**Host emails:** registration and login validate a simple `user@domain.tld` shape; addresses are **normalized to lowercase** (duplicate detection is case-insensitive).

## Cursor Cloud specific instructions

### Prerequisites (already handled by update script)

- Docker must be running (`sudo dockerd` if not started).
- PostgreSQL container: `sudo docker compose up -d postgres` (port **5434**).
- Python deps: `pip install -r requirements.txt` (uses system Python 3.12).
- Node deps: `npm install` (root) + `npm install --prefix frontend`.

### Starting services

```bash
# Terminal 1 – API (use python3, not python)
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 – Frontend
cd frontend && npm run dev:3055
```

Or combined: `npm run dev` (uses `concurrently`; requires `python3` on PATH).

### Gotchas

- The VM has `python3` but **no** `python` symlink. Use `python3` explicitly or alias it.
- On first startup, `sentence-transformers` downloads a model into `~/.cache/`; watchfiles may trigger a reload storm for ~30 seconds — the API is still reachable during this.
- `passlib` logs a benign bcrypt warning (`AttributeError: module 'bcrypt' has no attribute '__about__'`). Auth still works.
- The dev seed user (`dev@touristguide.local` / `devlogin123`) may fail login if bcrypt hash stored at startup differs from passlib runtime expectations. Register a new user instead for testing.

### Running tests

```bash
export ENVIRONMENT=development DISABLE_RATE_LIMIT=1 SKIP_SENTENCE_TRANSFORMERS=1
export TOURISTGUIDE_PYTEST=1 RUN_POSTGRES_TESTS=1 USE_POSTGRESQL=true
export POSTGRES_SERVER=localhost POSTGRES_PORT=5434
python3 -m pytest tests/ -q --tb=short
```

Or use `bash scripts/ci-smoke-backend.sh` (starts Postgres container automatically).

### Lint

- Python: `python3 -m compileall -q app` (zero errors = pass).
- Frontend: `cd frontend && npx eslint` (warnings only, no errors expected).
