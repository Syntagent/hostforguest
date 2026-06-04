# HostForGuest — Task backlog (living doc)

Last updated: 2026-06-04 (stabilization sprint)

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

## Open — next sprint

### 1. Event scraper production config

- Prod logs: `No Google AI API key found` — set `GOOGLE_AI_API_KEY` (or disable LLM enrichment) for event date extraction.
- `visitlovran.com` returns **403** to scraper — add User-Agent / retry policy or alternate source.
- Migrate off deprecated `google.generativeai` → `google.genai` (`ai_service.py` FutureWarning).

### 2. Database migrations (manual on prod if not auto-applied)

- `migrations/create_host_compliance_tables.sql`
- `migrations/add_property_rules_to_host_profiles.sql`
- `scripts/migrate_local_events_tables.py` for local events tables

Run via existing migration workflow; do not change schemas without need.

### 3. QA / E2E expansion

- Host tabs: Accommodation, Compliance (new), Insights events
- Guest: stay tab, saved events, preferences `[accessCode]` route
- Playwright: `tests/e2e/playwright.local.config.ts` for local 3055 runs

### 4. Routes / map polish (if gaps remain)

- Drag-reorder TNT points on map
- Click-to-add waypoint from map UI

## Local dev (canonical)

- UI: http://127.0.0.1:3055 — `npm run dev:frontend`
- API: http://localhost:8000 — `npm run dev:api`
- Smoke: `bash scripts/ci-smoke-backend.sh`

See `AGENTS.md` and `.cursor/rules/touristguide-local-dev.mdc`.
