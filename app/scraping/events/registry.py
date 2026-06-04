"""Registry of event scraper implementations."""

from __future__ import annotations

from typing import Dict, Type

from app.scraping.events.base import BaseEventScraper

EVENT_SCRAPER_REGISTRY: Dict[str, Type[BaseEventScraper]] = {}


def register_event_scraper(slug: str):
    def decorator(cls: Type[BaseEventScraper]) -> Type[BaseEventScraper]:
        EVENT_SCRAPER_REGISTRY[slug.strip().lower()] = cls
        cls.slug = slug.strip().lower()
        return cls

    return decorator


def get_event_scraper(scraper_class: str, source: dict) -> BaseEventScraper:
    key = scraper_class.strip().lower().replace("-", "_")
    cls = EVENT_SCRAPER_REGISTRY.get(key)
    if not cls:
        raise KeyError(f"No event scraper registered for: {scraper_class}")
    return cls(source=source)
