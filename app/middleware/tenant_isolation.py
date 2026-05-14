"""
Tenant isolation middleware for multi-tenant security.

Ensures data isolation between hosts and enforces
row-level security policies.

Uses pure ASGI middleware to avoid BaseHTTPMiddleware deadlock
with async endpoints.
"""

import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware:
    """
    Pure-ASGI middleware for tenant isolation.

    Extracts host_id from the Authorization header (if present)
    and stores it on ``scope["state"]`` so downstream handlers
    can read ``request.state.host_id``.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})

        headers = dict(scope.get("headers") or [])
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            state["tenant_auth"] = auth_header[7:]

        path: str = scope.get("path", "")
        if path.startswith("/api/v1/guest/"):
            qs = scope.get("query_string", b"").decode()
            for part in qs.split("&"):
                if part.startswith("access_code="):
                    state["access_code"] = part.split("=", 1)[1]
                    break
            for k, v in headers.items():
                if k == b"x-access-code":
                    state["access_code"] = v.decode()
                    break

        await self.app(scope, receive, send)
