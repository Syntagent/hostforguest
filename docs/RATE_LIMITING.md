# Rate limiting

## Current behavior

- `RateLimitingMiddleware` (`app/middleware/rate_limiting.py`) applies **in-memory** per-IP limits for HTTP requests.
- Limits are **per API process**. Multiple replicas behind a load balancer each maintain separate counters—clients may receive **up to N × limit** effective throughput.
- **Channel webhooks** are excluded from this limiter (dedicated path prefix).
- **Maintenance cron jobs** (`/api/v1/maintenance/jobs`) are excluded so scheduled `POST .../run-preventive-global` calls are not throttled by the in-app limiter.
- **Pytest / automation:** When `PYTEST_CURRENT_TEST` is set (during pytest) or `DISABLE_RATE_LIMIT=1`, limits are skipped so full test suites are not flaky with HTTP 429.

## Production guidance

- For horizontal scale, enforce primary rate limits at the **edge** (reverse proxy, **Cloudflare**, API gateway) or move to a **shared store** (e.g. Redis) if you keep in-app limiting.
- Keep default app limits conservative for anonymous traffic; tune webhook and authenticated routes separately if needed.
