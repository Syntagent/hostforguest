# Agent / developer rules — read before running the app

## Non‑negotiable: local development (stop the Docker mess)

1. **Develop on the host.** UI **http://127.0.0.1:3055**, API **http://localhost:8000** (or `127.0.0.1:8000`).
2. **Do not** use Docker `api` / `frontend` for day‑to‑day coding. They steal **8000** / **3001** and you will debug the wrong process.
3. If containers were started: `docker compose stop api frontend` (Postgres can stay up).
4. **`.env`:** `NEXT_PUBLIC_API_URL=http://localhost:8000` — must match the uvicorn port.
5. **Sanity check:** `http://localhost:8000/api/v1/docs` (not `/docs`).

**Commands:** repo root `npm run dev` *or* two terminals: `npm run dev:api` + `npm run dev:frontend`.

Full detail: **`.cursor/rules/touristguide-local-dev.mdc`** (always applied in Cursor).

**Tests:** full `pytest` sets `PYTEST_CURRENT_TEST` so in-app rate limiting is skipped; you can also set `DISABLE_RATE_LIMIT=1`. CI smoke also sets **`TOURISTGUIDE_PYTEST=1`** so app lifespan skips real Postgres bootstrap (tests use SQLite via `tests/conftest.py`). See **`docs/RATE_LIMITING.md`** for production vs multi-instance behavior.

**CI smoke (same list as GitHub Actions):** repo root **`npm run test:ci-smoke`** (Windows) or **`npm run test:ci-smoke:sh`** / **`bash scripts/ci-smoke-backend.sh`** — paths live in **`scripts/ci-smoke-backend.txt`** (edit that file to widen or narrow coverage).

**Preventive maintenance (cron):** set **`MAINTENANCE_JOB_SECRET`** in `.env`, then either run **`python scripts/run_maintenance_preventive.py`** daily, or `POST /api/v1/maintenance/jobs/run-preventive-global` with header **`X-Maintenance-Job-Secret`** (same value). Opens due issues from `maintenance_schedules` for all hosts.

**Adaptation “Analyze (AI)”:** needs a working AI provider. With **`PREFERRED_AI_PROVIDER=google`** (or `both`), **`GOOGLE_AI_API_KEY`** enables Gemini (structured JSON + optional before-photo **vision** when you add public **HTTPS** image URLs). With **`openai`**, use **`OPENAI_API_KEY`** — same vision path via OpenAI **`json_object`** + image attachments. Indicative only; not a quote.

**Host emails:** registration and login validate a simple `user@domain.tld` shape; addresses are **normalized to lowercase** (duplicate detection is case-insensitive).

---

## 🤖 Agent Guardrails (Karpathy Method v1)

> H1-specific: cursor-agent at ~/.local/bin/cursor-agent, Codex at /usr/bin/codex.

### Always Do
- Run tests before considering any task done
- Verify imports: python -c "from app.models import *"
- Include self-verification in every multi-step task
- Register all new endpoints in api.py

### Ask First
- Schema changes (new models, ALTER TABLE)
- Production deployment changes
- New dependencies
- Architecture changes

### Never Do
- NEVER modify production database without explicit confirmation
- NEVER force push to main/master
- NEVER use non-ASCII characters in byte literals (b"čšž" is SyntaxError)
- NEVER leave SQLAlchemy models without quoted tablenames/foreign keys
- NEVER create unregistered API endpoints

### Verification
Before submitting any work:
1. Run tests
2. Verify imports: python -c "from app.models import *"
3. Check unregistered endpoints: grep -rn "router =" backend/app/api/v1/endpoints/
4. Build check: docker compose build 2>&1 | tail -3

### Critical Pitfalls
1. SQLAlchemy quoting: __tablename__ = "users" NOT __tablename__ = users
2. Byte literals: b"hello" OK, b"čšž" is SyntaxError — use .encode("utf-8")
3. Usage limit: gpt-5.5-medium monthly cap — fallback to composer-2.5
4. Never stop mid-task: DO NOT ASK questions — complete the full scope
