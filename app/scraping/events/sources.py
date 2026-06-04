"""Load national event source definitions from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, TypedDict

import yaml

_CANDIDATE_PATHS = [
    Path(__file__).resolve().parents[3] / "infra" / "event_sources" / "national.yaml",
    Path("/app/infra/event_sources/national.yaml"),
    Path(__file__).resolve().parents[2] / ".." / "infra" / "event_sources" / "national.yaml",
]


class EventSourceDefinition(TypedDict, total=False):
    slug: str
    name: str
    url: str
    listing_url: str
    region: str | None
    city: str | None
    frequency_minutes: int
    enabled: bool
    scraper_class: str
    legal_notes: str
    insecure_ssl: bool


def load_national_event_sources(path: Path | None = None) -> list[EventSourceDefinition]:
    target = path
    if target is None:
        target = next((p for p in _CANDIDATE_PATHS if p.exists()), None)
    if target is None or not target.exists():
        return []

    data: Any = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("national.yaml must contain a list")

    out: list[EventSourceDefinition] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get("enabled") is False:
            continue
        if "slug" not in entry or "url" not in entry:
            continue
        item: EventSourceDefinition = EventSourceDefinition(
            slug=str(entry["slug"]),
            name=str(entry.get("name") or entry["slug"]),
            url=str(entry["url"]),
            listing_url=str(entry.get("listing_url") or entry["url"]),
            region=entry.get("region"),
            city=entry.get("city"),
            frequency_minutes=int(entry.get("frequency_minutes", 1440)),
            enabled=True,
            scraper_class=str(entry.get("scraper_class") or entry["slug"]).replace("-", "_"),
            legal_notes=str(entry.get("legal_notes") or ""),
        )
        if entry.get("insecure_ssl"):
            item["insecure_ssl"] = True
        out.append(item)
    return out
