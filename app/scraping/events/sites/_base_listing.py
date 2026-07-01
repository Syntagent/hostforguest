"""Listing scraper: Gemma4 extraction first, optional CSS fallback."""

from __future__ import annotations

import os
from typing import List

from app.scraping.events.base import BaseEventScraper
from app.scraping.events.filters import filter_event_drafts, scrape_quality_score
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.scraping.events.sites._listing import parse_article_cards


def _llm_extraction_enabled() -> bool:
    return os.getenv("EVENTS_LLM_EXTRACTION", "1").strip().lower() not in ("0", "false", "no")


def _selector_fallback_enabled() -> bool:
    # Off by default — CSS parsing caused navigation junk; LLM is the extractor.
    return os.getenv("EVENTS_SELECTOR_FALLBACK", "0").strip().lower() in ("1", "true", "yes")


class ConfigurableListingScraper(BaseEventScraper):
    """Fetch listing HTML and extract events via Gemma4; CSS parsers are fallback only."""

    item_selector: str = "article, .event-item, .event, .dogadanje, li.event"
    title_selector: str = "h2, h3, .title, a"
    date_selector: str = ".date, time, .event-date, .datum"
    desc_selector: str = "p, .description, .excerpt"
    min_events: int = 1

    def _parse_listing_impl(self, html: str, *, base_url: str) -> List[LocalEventDraft]:
        """CSS card parser — used for tests and when LLM is unavailable."""
        cfg = self.source
        drafts = parse_article_cards(
            html,
            base_url=base_url,
            item_selector=str(cfg.get("item_selector") or self.item_selector),
            title_selector=str(cfg.get("title_selector") or self.title_selector),
            date_selector=str(cfg.get("date_selector") or self.date_selector),
            desc_selector=str(cfg.get("desc_selector") or self.desc_selector),
            default_city=cfg.get("city"),
            default_region=cfg.get("region"),
        )
        return filter_event_drafts(drafts)

    async def run(self) -> List[LocalEventDraft]:
        listing = self.listing_url()
        result = await self.fetch_html(listing)
        drafts: List[LocalEventDraft] = []

        if _llm_extraction_enabled():
            from app.services.event_extraction_refiner import EventExtractionRefiner

            refiner = EventExtractionRefiner()
            llm_drafts = await refiner.extract_from_html(
                result.html,
                page_url=listing,
                city=self.source.get("city"),
                region=self.source.get("region"),
            )
            if llm_drafts:
                return llm_drafts

        if _selector_fallback_enabled():
            drafts = self._parse_listing_impl(result.html, base_url=listing)

        return drafts
