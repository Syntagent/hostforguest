"""Visit Lovran / TZ Lovran — događanja listing (visitlovran.com)."""

from __future__ import annotations

from typing import List
from urllib.parse import urljoin

from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper
from app.scraping.events.sites._listing import parse_article_cards


@register_event_scraper("tz_lovran")
class TzLovranScraper(ConfigurableListingScraper):
    """Avia/Enfold grid on visitlovran.com/dogadanja/."""

    item_selector = "article.inner-entry, article.main_color"
    title_selector = "h3.entry-title, h3.grid-entry-title, .entry-title"
    date_selector = "time, .post-date, .entry-date, span.date"
    desc_selector = ".entry-content p, .grid-content p, .excerpt"

    def _parse_listing_impl(self, html: str, *, base_url: str) -> List:
        base = base_url.rstrip("/")
        if "visitlovran.com" not in base:
            base = "https://visitlovran.com"
        listing = f"{base}/dogadanja/"
        drafts = parse_article_cards(
            html,
            base_url=listing,
            item_selector=self.item_selector,
            title_selector=self.title_selector,
            date_selector=self.date_selector,
            desc_selector=self.desc_selector,
            default_city=self.source.get("city") or "Lovran",
            default_region=self.source.get("region") or "Kvarner",
        )
        # Fix relative links
        for d in drafts:
            if d.url and d.url.startswith("/"):
                d.url = urljoin(listing, d.url)
        return drafts
