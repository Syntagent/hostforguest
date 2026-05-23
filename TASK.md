# HostForGuest Task Notes

## Ready For Distribution

- [x] Sanitized hardcoded browser API key from the support app.
- [x] Added `DEPLOYMENT.md`.
- [x] Parameterized Docker Compose database credentials.
- [x] Added support app lockfile.
- [x] Published a clean-history snapshot to `https://github.com/Syntagent/hostforguest`.
- [x] Removed obsolete workflow references from active code and public docs.

## Completed (2026-05-21)

- [x] **CI smoke script** — `scripts/ci-smoke-backend.sh` now prefers `.venv/bin/python` (falls back to `python3`/`python`) and starts compose Postgres before pytest.
- [x] **Live API tests** — `tests/test_event_recommendations.py` skipped unless `RUN_LIVE_API_TESTS=1` (avoids false failures when no API on `8006`).
- [x] **PostgreSQL regression pass** — `scripts/run-postgres-regression.sh` (compose Postgres on `localhost:5434`, `RUN_POSTGRES_TESTS=1`). Fixed `import_models()` ordering, `attraction_host_contributions` DDL, unified test/app engine on Postgres, `NullPool`, integration module single reset. **429 passed**, 14 skipped. Commit `a71d004` (2026-05-21).
- [x] **Remove SQLite test path** — Deleted `tests/test_event_recommendations_sqlite.py`; `tests/conftest.py` and CI smoke use PostgreSQL only (no in-memory SQLite).

## Completed (2026-05-22)

- [x] **Production reverse-proxy example** — `deploy/nginx/hostforguest.conf.example`, `deploy/caddy/Caddyfile.example`, **[docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md)** (path routing, port maps, Cloudflare cross-links, migration apply loop), CI contract test `tests/test_deploy_reverse_proxy_examples.py`.

## Completed (2026-05-22, continued)

- [x] **`scripts/apply-migrations.sh`** — Bash migration runner (parity with `apply_migrations.ps1`); dry-run works without `psql`; `tests/test_apply_migrations_script.py`.

## Completed (2026-05-23)

- [x] **Guest events Playwright CI** — `scripts/seed_e2e_guest.py` + `scripts/run-e2e-ci.sh` + `tests/e2e/ci-guest-events.spec.ts` (local stack on **8000/3055**); GitHub Actions job `e2e-guest-events`; contract test `tests/test_e2e_ci_harness.py`. Ben/production specs under `tests/e2e/ben_*.spec.ts` remain for manual runs against deployed env.

## Next Technical Work
- [ ] Review frontend build output and remove generated service-worker files if they are not intentionally source-controlled.
- [ ] Decide whether `.cursor/plans` should stay in the public repo.

## Top impact candidates (for next session)

1. Extend CI guest E2E to host dashboard smoke (dev login + overview tab) using the same harness pattern.

## Validation Commands

```bash
docker compose config --quiet
python -m compileall -q app
bash scripts/ci-smoke-backend.sh
bash scripts/run-postgres-regression.sh    # full pytest on compose Postgres (excludes tests/e2e)
npm run test:e2e:ci                      # Playwright guest events smoke (8000 + 3055)
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
