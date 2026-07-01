"""Local events scraping framework."""

from app.scraping.events.registry import EVENT_SCRAPER_REGISTRY, get_event_scraper
from app.scraping.events.sources import EventSourceDefinition, load_national_event_sources

__all__ = [
    "EVENT_SCRAPER_REGISTRY",
    "get_event_scraper",
    "EventSourceDefinition",
    "load_national_event_sources",
]
