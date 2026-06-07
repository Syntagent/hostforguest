"""Base class for per-site event scrapers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional

from app.scraping.events.policies import PoliteCrawler, PoliteCrawlerConfig, ScrapingError
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.scraping.events.sources import EventSourceDefinition


@dataclass(slots=True)
class EventScrapeResult:
    url: str
    fetched_at: datetime
    html: str
    status_code: int = 200
    error: Optional[str] = None


class BaseEventScraper(ABC):
    """Parse event listings from a configured tourism source."""

    slug: str = "base"

    def __init__(
        self,
        *,
        source: EventSourceDefinition | Mapping[str, Any] | None = None,
        policy: Optional[PoliteCrawler] = None,
    ) -> None:
        self.source: dict[str, Any] = dict(source or {})
        if policy is None and (
            self.source.get("insecure_ssl")
            or self.source.get("user_agent")
            or self.source.get("headers")
        ):
            policy = PoliteCrawler(
                config=PoliteCrawlerConfig(
                    verify_ssl=not bool(self.source.get("insecure_ssl")),
                    user_agent=str(self.source.get("user_agent") or PoliteCrawlerConfig.user_agent),
                    headers=dict(self.source.get("headers") or {}),
                )
            )
        self._policy = policy or PoliteCrawler()

    @property
    def policy(self) -> PoliteCrawler:
        return self._policy

    def listing_url(self) -> str:
        return str(self.source.get("listing_url") or self.source.get("url") or "")

    async def fetch_html(self, url: str) -> EventScrapeResult:
        if not url:
            raise ScrapingError("No URL configured for scraper")
        try:
            response = await self.policy.fetch(url)
            return EventScrapeResult(
                url=url,
                fetched_at=datetime.now(timezone.utc),
                html=response.text,
                status_code=response.status_code,
            )
        except Exception as exc:
            raise ScrapingError(f"{url} failed: {exc}") from exc

    async def run(self) -> List[LocalEventDraft]:
        """Fetch listing page and parse events."""
        listing = self.listing_url()
        result = await self.fetch_html(listing)
        return self.parse_listing(result.html, base_url=listing)

    def parse_listing(self, html: str, *, base_url: str) -> List[LocalEventDraft]:
        """Parse listing HTML (also used by tests with fixtures)."""
        return self._parse_listing_impl(html, base_url=base_url)

    @abstractmethod
    def _parse_listing_impl(self, html: str, *, base_url: str) -> List[LocalEventDraft]:
        ...
