"""tz-lovran listing fixture parses dated events."""

from __future__ import annotations

from pathlib import Path

import app.scraping.events.sites  # noqa: F401
from app.scraping.events.registry import get_event_scraper
from app.scraping.events.sources import load_national_event_sources

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "events" / "tz_lovran" / "listing.html"


def test_tz_lovran_fixture_parses_events_with_dates():
    defn = next(s for s in load_national_event_sources() if s["slug"] == "tz-lovran")
    scraper = get_event_scraper(defn["scraper_class"], defn)
    html = FIXTURE.read_text(encoding="utf-8")
    drafts = scraper.parse_listing(html, base_url=defn["listing_url"])
    assert len(drafts) >= 1
    dated = [d for d in drafts if d.start_at is not None]
    assert len(dated) >= 1
    assert any("marunada" in d.title.lower() for d in drafts), drafts
