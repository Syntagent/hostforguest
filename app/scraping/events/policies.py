"""Polite HTTP fetching for event scrapers."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx


@dataclass
class PoliteCrawlerConfig:
    delay_seconds: float = 1.0
    timeout_seconds: float = 25.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    max_retries: int = 2
    backoff_factor: float = 1.0
    retry_statuses: tuple[int, ...] = (403, 429, 500, 502, 503, 504)
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)


class PoliteCrawler:
    """Per-host rate-limited httpx client."""

    def __init__(
        self,
        *,
        config: Optional[PoliteCrawlerConfig] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.config = config or PoliteCrawlerConfig()
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
            **self.config.headers,
        }
        self._client = (
            client
            if client is not None
            else httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                headers=headers,
                follow_redirects=True,
                verify=self.config.verify_ssl,
            )
        )
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_seen: dict[str, float] = {}

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "PoliteCrawler":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        parsed = urlparse(url)
        domain = parsed.netloc
        lock = self._locks.setdefault(domain, asyncio.Lock())
        async with lock:
            await self._respect_delay(domain)
            attempt = 0
            while True:
                try:
                    response = await self._client.get(url, **kwargs)
                    if response.status_code in self.config.retry_statuses:
                        response.raise_for_status()
                    if response.status_code >= 400:
                        response.raise_for_status()
                    self._last_seen[domain] = time.monotonic()
                    return response
                except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                    if attempt >= self.config.max_retries:
                        raise
                    attempt += 1
                    await asyncio.sleep(self.config.backoff_factor * (2 ** (attempt - 1)))

    async def _respect_delay(self, domain: str) -> None:
        last = self._last_seen.get(domain)
        if last is None:
            return
        elapsed = time.monotonic() - last
        if elapsed < self.config.delay_seconds:
            await asyncio.sleep(self.config.delay_seconds - elapsed)


class ScrapingError(Exception):
    """Raised when event scraping fails."""
