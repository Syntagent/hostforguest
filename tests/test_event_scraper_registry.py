"""Every enabled national.yaml slug must resolve to a scraper class."""

from __future__ import annotations

import pytest

import app.scraping.events.sites  # noqa: F401
from app.scraping.events.registry import EVENT_SCRAPER_REGISTRY, get_event_scraper
from app.scraping.events.sources import load_national_event_sources

pytestmark = pytest.mark.no_db


def test_all_enabled_sources_have_scrapers():
    sources = load_national_event_sources()
    assert len(sources) >= 5
    for src in sources:
        key = src["scraper_class"].replace("-", "_")
        assert key in EVENT_SCRAPER_REGISTRY, f"missing scraper for {src['slug']}"
        scraper = get_event_scraper(src["scraper_class"], src)
        assert scraper.listing_url()
