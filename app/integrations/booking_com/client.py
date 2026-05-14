"""
HTTP client for Booking.com Connectivity-style APIs.

Uses Basic auth. Set BOOKING_COM_MOCK=true to avoid real network (tests / local without credentials).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.integrations.booking_com import mappers

logger = logging.getLogger(__name__)


class BookingComClient:
    """Thin async client with retries and optional mock mode."""

    def __init__(
        self,
        username: str,
        password: str,
        base_url: Optional[str] = None,
    ):
        self.username = username or ""
        self.password = password or ""
        self.base_url = (base_url or settings.booking_com_api_base).rstrip("/")
        self._mock = os.environ.get("BOOKING_COM_MOCK", "").lower() in ("1", "true", "yes")
        if not self.username or not self.password:
            self._mock = True
            logger.info("Booking.com client running in mock mode (missing credentials)")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        content: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        if self._mock:
            return self._mock_response(method, path, content)

        url = f"{self.base_url}{path}"
        timeout = settings.booking_com_request_timeout_seconds
        last_exc: Optional[Exception] = None
        for attempt in range(max(1, settings.booking_com_max_retries)):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(
                        method,
                        url,
                        content=content,
                        headers=headers or {},
                        auth=(self.username, self.password),
                    )
                if resp.status_code == 429:
                    await asyncio.sleep(2**attempt)
                    continue
                return resp
            except httpx.RequestError as e:
                last_exc = e
                await asyncio.sleep(min(2**attempt, 30))
        raise last_exc or RuntimeError("Booking.com request failed")

    def _mock_response(self, method: str, path: str, content: Optional[str]) -> httpx.Response:
        body = (
            '{"reservations":[{"id":"mock-res-1","hotel_id":"mock-hotel","room_id":"mock-room",'
            '"status":"confirmed","check_in":"2026-04-01","check_out":"2026-04-05",'
            '"currency":"EUR","total_price":400,"guest_name":"Mock Guest",'
            '"modified_at":"2026-03-20 12:00:00"}]}'
        )
        if "reservation" in path.lower():
            return httpx.Response(200, content=body, request=httpx.Request(method, path))
        return httpx.Response(200, content='{"ok":true}', request=httpx.Request(method, path))

    async def fetch_reservations(
        self,
        hotel_id: str,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Pull reservations. Real deployments should call the specific Connectivity endpoint
        agreed with Booking.com; here we use a placeholder path and parse JSON/XML.
        """
        path = f"/hotels/json/reservations?hotel_id={hotel_id}"
        if cursor:
            path += f"&cursor={cursor}"
        resp = await self._request("GET", path)
        text = resp.text
        if not resp.is_success:
            logger.error("Booking.com reservations error %s: %s", resp.status_code, text[:500])
            return [], cursor
        text_stripped = text.strip()
        if text_stripped.startswith("{"):
            try:
                rows = mappers.reservations_from_mock_json(text)
            except Exception as e:
                logger.warning("JSON parse failed: %s", e)
                rows = []
        elif text_stripped.startswith("<"):
            rows = mappers.reservations_from_xml(text)
        else:
            rows = []
        next_cursor = None
        if cursor and rows:
            next_cursor = str(int(cursor or "0") + len(rows))
        elif rows:
            next_cursor = str(len(rows))
        return rows, next_cursor

    async def push_availability(self, payload: Dict[str, Any]) -> bool:
        """Push availability update (placeholder path)."""
        import json

        body = json.dumps(payload)
        resp = await self._request(
            "POST",
            "/hotels/json/availability",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        return resp.is_success

    async def push_rates(self, payload: Dict[str, Any]) -> bool:
        import json

        body = json.dumps(payload)
        resp = await self._request(
            "POST",
            "/hotels/json/rates",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        return resp.is_success
