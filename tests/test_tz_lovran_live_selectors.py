"""Live fetch test for Visit Lovran selectors (skip without network)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_SCRAPER_TESTS", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set RUN_LIVE_SCRAPER_TESTS=1 to hit visitlovran.com",
)


@pytest.mark.asyncio
async def test_visit_lovran_listing_has_real_events():
    import app.scraping.events.sites  # noqa: F401
    from app.scraping.events.registry import get_event_scraper
    from app.scraping.events.sources import load_national_event_sources

    defn = next(s for s in load_national_event_sources() if s["slug"] == "tz-lovran")
    scraper = get_event_scraper(defn["scraper_class"], defn)
    async with scraper.policy:
        drafts = await scraper.run()
    titles = [d.title.lower() for d in drafts]
    assert any("marunada" in t for t in titles), f"expected Marunada in {titles[:8]}"
    assert not any(t.startswith("dolazak") for t in titles)
