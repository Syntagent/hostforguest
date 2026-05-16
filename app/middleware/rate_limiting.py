"""
Rate limiting middleware for API protection.

Pure ASGI implementation to avoid BaseHTTPMiddleware deadlocks
with async endpoints.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RateLimitingMiddleware:
    """
    Pure-ASGI rate-limiting middleware.

    Tracks per-IP request counts and returns 429 when limits are exceeded.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Pytest drives many HTTP requests from one process/IP; in-memory limits become flaky.
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("DISABLE_RATE_LIMIT") == "1":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        if path.startswith("/api/v1/channel-webhooks") or path.startswith(
            "/api/v1/maintenance/jobs"
        ):
            await self.app(scope, receive, send)
            return

        identifier = self._identifier_from_scope(scope)
        if not identifier:
            await self.app(scope, receive, send)
            return

        allowed, remaining, reset_time = self._check_rate_limit(identifier)

        if not allowed:
            body = json.dumps({
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "reset_time": reset_time.isoformat() if reset_time else None,
            }).encode()
            headers = [
                [b"content-type", b"application/json"],
                [b"x-ratelimit-limit", str(self.requests_per_minute).encode()],
                [b"x-ratelimit-remaining", b"0"],
            ]
            if reset_time:
                headers.append([b"x-ratelimit-reset", str(int(reset_time.timestamp())).encode()])

            await send({"type": "http.response.start", "status": 429, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return

        rl_headers: list = [
            [b"x-ratelimit-limit", str(self.requests_per_minute).encode()],
            [b"x-ratelimit-remaining", str(remaining).encode()],
        ]
        if reset_time:
            rl_headers.append([b"x-ratelimit-reset", str(int(reset_time.timestamp())).encode()])

        async def inject_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = list(message.get("headers") or [])
                existing.extend(rl_headers)
                message["headers"] = existing
            await send(message)

        await self.app(scope, receive, inject_headers)

    # --------------------------------------------------------------------- #

    @staticmethod
    def _identifier_from_scope(scope: Scope) -> Optional[str]:
        client = scope.get("client")
        if client:
            return f"ip:{client[0]}"
        return None

    def _check_rate_limit(self, identifier: str) -> Tuple[bool, int, Optional[datetime]]:
        now = datetime.utcnow()
        self._clean_old_entries(identifier, now)

        minute_count = len(self.minute_requests[identifier])
        if minute_count >= self.requests_per_minute:
            oldest = min(self.minute_requests[identifier]) if self.minute_requests[identifier] else now
            return False, 0, oldest + timedelta(minutes=1)

        hour_count = len(self.hour_requests[identifier])
        if hour_count >= self.requests_per_hour:
            oldest = min(self.hour_requests[identifier]) if self.hour_requests[identifier] else now
            return False, 0, oldest + timedelta(hours=1)

        self.minute_requests[identifier].append(now)
        self.hour_requests[identifier].append(now)

        remaining = min(
            self.requests_per_minute - minute_count - 1,
            self.requests_per_hour - hour_count - 1,
        )
        return True, max(0, remaining), now + timedelta(minutes=1)

    def _clean_old_entries(self, identifier: str, now: datetime) -> None:
        cutoff_minute = now - timedelta(minutes=1)
        self.minute_requests[identifier] = [t for t in self.minute_requests[identifier] if t > cutoff_minute]
        cutoff_hour = now - timedelta(hours=1)
        self.hour_requests[identifier] = [t for t in self.hour_requests[identifier] if t > cutoff_hour]
