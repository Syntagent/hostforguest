# HostForGuest — Task backlog (living doc)

Last updated: 2026-06-07 (production startup / migrations)

## Production status (H1 VPS)

| Service | Container | Status |
|---------|-----------|--------|
| API | `hostforguest_prod_api` | healthy — `:8006` |
| Frontend | `hostforguest_prod_frontend` | healthy — `:3007` |
| Postgres | `hostforguest_prod_postgres` | healthy — `:5439` |
| Channel sync | `hostforguest_prod_channel_sync` | healthy |
| Event sync | `hostforguest_prod_event_sync` | healthy (was restarting — fixed) |

Public: https://hostforguest.syntagent.com

Deploy: `docker compose -p hostforguest-prod -f docker-compose.yml -f docker-compose.vps-prod.yml --profile docker-api up -d --build`

## Completed this sprint

- **event_sync crash** — removed nested `import os` in `app/tasks/event_sync_runner.py` (UnboundLocalError).
- **Seasonal recommendations** — candidates filtered by `request.season`, not wall-clock month (`recommendation_candidates.py`).
- **Feature commit** — `8af5831`: event scraper, compliance, voice/accommodation agent, guest stay, dashboard tab URL, E2E harness updates.
- **CI smoke** — 251 passed (see `scripts/ci-smoke-backend.txt`).
- **Deploy** — prod stack rebuilt; all `hostforguest_prod_*` containers healthy.

## Prior QA sprint (already shipped — keep for reference)

- Auto-geocode / onboarding geocode fallback
- Dashboard perf (skeletons, consolidated stats)
- Guest groups CRUD fixes + E2E
- Routes save + TNT points
- `channel_sync` health when 0 accounts

## Completed follow-up — 2026-06-07

- **Event scraper production config** — Lovran listing moved to the working official path, crawler now uses browser-like headers, retries `403`/`429`, and raises final HTTP errors instead of parsing error pages.
- **Gemini SDK migration** — `ai_service.py` and fallback structured AI paths now use `google.genai`; deprecated `google-generativeai` was removed from runtime requirements.
- **Migration workflow** — `create_host_compliance_tables.sql` added to `migrations/MIGRATION_ORDER.txt`.
- **QA / E2E expansion** — local Playwright config now includes host dashboard, guest events, and onboarding geocode specs; host Compliance/Accommodation and guest stay/preferences redirect coverage added.
- **Fast test hygiene** — source-only tests can use `pytest.mark.no_db` to skip the autouse PostgreSQL schema reset.
- **Production startup health** — API/OpenAI imports are lazy, Docker healthchecks use lightweight listener checks, and the stack was redeployed healthy behind Cloudflare.
- **Production migrations** — compliance tables, `host_profiles.property_rules`, `local_events`, and `event_source_proposals` verified on prod DB.

## Open — next sprint

### 1. Routes / map polish (if gaps remain)

- Drag-reorder TNT points on map
- Click-to-add waypoint from map UI

## Local dev (canonical)

- UI: http://127.0.0.1:3055 — `npm run dev:frontend`
- API: http://localhost:8000 — `npm run dev:api`
- Smoke: `bash scripts/ci-smoke-backend.sh`

See `AGENTS.md` and `.cursor/rules/touristguide-local-dev.mdc`.
