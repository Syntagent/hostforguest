# Tenant isolation contract (application layer)

This project **does not enforce PostgreSQL row-level security (RLS)** in production today. Isolation relies on **application code**: authenticated host session (`X-Session-Token`), guest access codes, and service-layer filters.

## Rules for new or changed endpoints

1. **Mutations and sensitive reads** on host-owned data must use `get_current_host`, `require_host_session`, or an equivalent that resolves the caller to a `Host` record—never trust a client-supplied `host_id` as authorization.
2. **Every query** that returns or updates tenant data must scope by `host_id` (or `guest_group_id` only after verifying that group belongs to the current host).
3. **Public or `get_db`-only routes** (see `docs/TENANT_ISOLATION_AUDIT.md`) must document why they are safe: rate limits, signed webhooks, access codes, or intentionally public data with no cross-tenant identifiers in the request.
4. **Guest flows** must validate `access_code` (or equivalent) before exposing any guest-group or itinerary data.
5. **Do not assume** `TenantIsolationMiddleware` sets `host_id`; it only forwards bearer/access-code fragments on the ASGI scope unless extended.

## Code review checklist (quick)

- [ ] Dependency is `get_current_host` / `require_host_session` / validated access code—not only `get_db`.
- [ ] Service method receives `host_id` from the authenticated context, not from unchecked JSON/query.
- [ ] List endpoints filter by host (or guest scope) in the service/repository layer.
- [ ] IDs in the path/body are checked for ownership before read/update/delete.

## Relation to RLS

When/if Postgres RLS is added, this contract remains the **primary** design for clarity; RLS becomes a safety net. Until then, `RLSService` is **not** active—see `app/services/rls_service.py` module docstring.
