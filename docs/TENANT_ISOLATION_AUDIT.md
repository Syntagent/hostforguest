# Tenant isolation audit

**Repository:** TouristGuideLocal / HostForGuest  
**Scope:** API v1 router wiring (`app/api/v1/api.py`), auth dependencies in v1 routers, `TenantIsolationMiddleware`, `RLSService`, SQL migrations under `migrations/*.sql`.

---

## 1) Executive summary

- **`RLSService`** (`app/services/rls_service.py`): The class exists to call `set_config('app.current_host_id', …)` on the DB session, but **nothing in the codebase imports or uses it** outside that file. So **no request path sets PostgreSQL tenant context** via this service.

- **PostgreSQL migrations** (`migrations/*.sql`): There are **no `ROW LEVEL SECURITY` / `CREATE POLICY` statements** and **no references to `app.current_host_id`** in those migration files. RLS is therefore **not enforced at the database layer** in this migration set.

- **`TenantIsolationMiddleware`** (`app/middleware/tenant_isolation.py`): For HTTP/WebSocket scopes it only copies **Bearer token text** into `scope["state"]["tenant_auth"]` (substring after `"Bearer "`) and, for paths starting with `/api/v1/guest/`, may set **`scope["state"]["access_code"]`** from query `access_code=` or header `x-access-code`. It does **not** resolve or store a `host_id`; the docstring mentions `request.state.host_id`, but the implementation does **not** set that key.

**Net:** Tenant boundaries today rely on **application-layer checks** (session token, optional HMAC on webhooks, access codes on specific flows), **not** on DB-enforced RLS or this middleware alone.

---

## 2) API route groups (`app/api/v1/api.py`) — prefix and inferred primary auth

Auth patterns are inferred from `Depends(...)` and imports in the listed router modules. **`get_current_host`** (canonical in `hosts.py`) means **`X-Session-Token`** session lookup unless noted. Some modules define their **own** `get_current_host` with the same session pattern.

| Prefix | Router module | Inferred primary auth / notes |
|--------|----------------|------------------------------|
| `/hosts` | `hosts.py` | **Mixed:** public register/login; protected routes use **`Depends(get_current_host)`** → **`X-Session-Token`**. |
| `/maintenance` | `maintenance.py` | **`get_current_host`** imported from `hosts` → session. |
| `/adaptation` | `adaptation.py` | **`get_current_host`** from `hosts` → session. |
| `/guest-groups` | `guest_groups.py` | **Local `get_current_host`** on CRUD-style endpoints. |
| `/attractions` | `attractions.py` | **Mixed:** explicit **public** list/search (`get_db` only); mutations use **local `get_current_host`**; some flows use **`access_code`**. |
| `/recommendations` | `recommendations.py` | **Local `get_current_host`** → session on main endpoints. |
| `/settings` | `settings.py` | **Local `get_current_host`** → session. |
| `/itineraries` | `itineraries.py` | **Local `get_current_host`** → session. |
| `/onboarding` | `host_onboarding.py` | **Mixed:** many routes use **`get_current_host_optional`**; stricter steps use **`get_current_host`**; guest-facing paths use **`access_code`** / `Host.guest_access_code` lookup. |
| `/realtime` | `realtime_data.py` | **Public-style** — **`get_db` only** in typical handlers. |
| `/locations` | `locations.py` | **`get_db` only** — routes keyed by IDs without `get_current_host` in many signatures. |
| `/vector` | `vector.py` | **`get_db` only** — no `get_current_host` / `require_host_session`. |
| `/partners` | `partners.py` | **Local `get_current_host`** → session. |
| `/cleaning` | `cleaning.py` | **Local `get_current_host`** → session. |
| `/content-generation` | `content_generation.py` | **`get_db` only** on many handlers. |
| `/analytics` | `analytics.py` | **`require_host_session`** from `app.core.auth`. |
| `/communications` | `communications.py` | **`require_host_session`**. |
| `/reviews` | `reviews.py` | **`get_db` only** on many handlers. |
| `/bookings` | `bookings.py` | **`get_db` only** — IDs in body/query. |
| `/subscriptions` | `subscriptions.py` | **`get_current_host`** from `hosts`. |
| `/bi` | `bi.py` | **`get_current_host`** from `hosts`. |
| `/audit` | `audit.py` | **`get_current_host`** from `hosts`. |
| `/performance` | `performance.py` | **`require_host_session`**. |
| `/channel-integrations` | `channel_integrations.py` | **`get_current_host`** from `hosts`. |
| `/channel-webhooks` | `channel_webhooks.py` | **HMAC signature** when `channel_webhook_secret` is set; **`get_db`** — not host session. |

---

## 3) Top five risks / gaps (plain language)

1. **Database does not enforce tenants:** Without RLS (and with `RLSService` unused), any bug or missing `WHERE host_id = …` in SQL can **expose another host’s rows** at the data layer.

2. **“Public” or DB-only routers widen blast radius:** Several prefixes (`/vector`, `/realtime`, parts of `/attractions`, `/locations`, `/bookings`, `/reviews`, `/content-generation`) rely on **`get_db` only** or documented public access — if services do not re-check ownership, **unauthenticated callers** may read or mutate data they should not.

3. **ID-in-URL / ID-in-body trust:** Endpoints that take **`guest_group_id`**, **`attraction_id`**, or **`host_id` from the client** without a consistent session gate are vulnerable to **ID guessing / cross-tenant access** unless every service method enforces ownership.

4. **Middleware does not isolate tenants:** `TenantIsolationMiddleware` stores **raw bearer substring** and **guest `access_code`** but is **not wired** to FastAPI `host_id` resolution; downstream code that never reads `scope["state"]` gets **no benefit**. Docstring vs. behavior (**no `host_id`**) is misleading for reviewers.

5. **Inconsistent auth primitives:** Mix of **`get_current_host`**, **`require_host_session`**, local duplicates of `get_current_host`, and **optional** host onboarding increases the chance one new endpoint picks the **wrong** dependency or skips scoping in the service layer.

---

## 4) Recommendation: Branch A (RLS) vs Branch B (app-layer contract)

**Branch A (RLS):** Add PostgreSQL RLS policies keyed on `app.current_host_id` (or equivalent), run `set_config` at the start of each request’s DB transaction, migrate tables to include policies, and add tests that prove cross-tenant reads fail at SQL level. This gives **defense in depth** but touches migrations, performance, and every table’s policy design.

**Branch B (app-layer contract):** Standardize on one host dependency (`get_current_host` or `require_host_session`), require it for all non-public routes, **ban** client-supplied `host_id` where possible, and enforce **`host_id` / `guest_group_id` ownership in services** with integration tests per domain; treat “public” routers explicitly (rate limits, API keys, or signed tokens). This is faster to roll out but **every new query** must remain correct — there is no database backstop.

**Pragmatic path:** Short term tighten **Branch B** (close `get_db`-only holes); medium term add **Branch A** for the highest-risk tables if multi-tenant isolation is a formal requirement.
