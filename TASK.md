# HostForGuest Task Notes

## Ready For Distribution

- [x] Sanitized hardcoded browser API key from the support app.
- [x] Added `DEPLOYMENT.md`.
- [x] Parameterized Docker Compose database credentials.
- [x] Added support app lockfile.
- [x] Published a clean-history snapshot to `https://github.com/Syntagent/hostforguest`.
- [x] Removed obsolete workflow references from active code and public docs.

## Completed (2026-05-21)

- [x] **Event recommendations CI coverage** — Added `tests/test_event_recommendations_sqlite.py` (in-memory SQLite + HTTP) for scoring, personalization payload, feed bootstrap, and QA-event filtering. Registered `content_source` models in `tests/conftest.py`. Added path to `scripts/ci-smoke-backend.txt`.
- [x] **CI smoke script** — `scripts/ci-smoke-backend.sh` now prefers `.venv/bin/python` (falls back to `python3`/`python`).
- [x] **Live API tests** — `tests/test_event_recommendations.py` skipped unless `RUN_LIVE_API_TESTS=1` (avoids false failures when no API on `8006`).

## Next Technical Work

- [ ] Run a full test pass against a fresh PostgreSQL stack.
- [ ] Add a production reverse-proxy example.
- [ ] Add database migration runner guidance for existing deployments.
- [ ] Review frontend build output and remove generated service-worker files if they are not intentionally source-controlled.
- [ ] Decide whether `.cursor/plans` should stay in the public repo.

## Top impact candidates (for next session)

1. Full PostgreSQL regression pass (`python -m pytest` against compose Postgres, not only SQLite).
2. Production reverse-proxy example (nginx/Caddy) aligned with `DEPLOYMENT.md` and Cloudflare tunnel docs.
3. Guest events UI E2E in Playwright wired into a non-interactive CI job (host + guest flows on 3055/8000).

## Validation Commands

```bash
docker compose config --quiet
python -m compileall -q app
.venv/bin/python -m pytest tests/test_event_recommendations_sqlite.py -q
bash scripts/ci-smoke-backend.sh
npm run build --prefix frontend
npm run build --prefix support_app/day_planner
```

## Deployment Checklist

- [ ] Create `.env` from `env.example`.
- [ ] Set strong `SECRET_KEY` and `POSTGRES_PASSWORD`.
- [ ] Set `POSTGRES_HOST_AUTH_METHOD=md5` or stronger outside local development.
- [ ] Set `NEXT_PUBLIC_API_URL` to the public API URL.
- [ ] Set `CORS_ORIGINS` to the frontend origin.
- [ ] Keep `BOOKING_COM_MOCK=true` until real channel credentials are ready.
