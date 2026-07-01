"""
Guest preference matching for local events (tags, age_group, event_type).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Set

from app.scraping.events.event_types import EVENT_TYPES

EVENT_TYPE_PRIORITY: Dict[str, int] = {
    "festival": 10,
    "concert": 9,
    "cultural": 8,
    "food_wine": 8,
    "market": 7,
    "sports": 6,
    "exhibition": 6,
    "film": 5,
    "kids": 5,
    "nature": 4,
    "workshop": 4,
    "other": 1,
}

FAMILY_KEYWORDS = ("djecom", "dječj", "djecj", "obitelj", "family", "kids", "children", "s djecom")
WINE_KEYWORDS = ("vino", "wine", "gastro", "cellar", "tasting", "hrana")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _event_tags(ev: Dict[str, Any]) -> Set[str]:
    raw = ev.get("tags") or ev.get("keywords") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(t).lower() for t in raw}


def preference_match_score(ev: Dict[str, Any], guest_text: str = "", guest_tags: Optional[Set[str]] = None) -> float:
    """Score 0..1 how well an event matches guest preferences."""
    blob = _norm(
        " ".join(
            str(ev.get(k) or "")
            for k in ("title", "description", "summary", "event_type", "age_group", "price")
        )
    )
    tags = _event_tags(ev)
    score = 0.0
    hits = 0

    text = _norm(guest_text)
    tag_set = guest_tags or set()

    if any(k in text for k in FAMILY_KEYWORDS) or tag_set & {"family", "kids", "children"}:
        if ev.get("age_group") in ("family", "kids"):
            hits += 2
        if tags & {"family", "kids"}:
            hits += 2
        if any(w in blob for w in ("dječj", "djecj", "obitelj", "family", "kids")):
            hits += 1

    if any(k in text for k in WINE_KEYWORDS) or "wine" in tag_set:
        if ev.get("event_type") == "food_wine":
            hits += 2
        if tags & {"wine", "gastro"}:
            hits += 2
        if any(w in blob for w in ("vino", "wine", "gastro")):
            hits += 1

    for tag in tag_set:
        if tag in tags or tag in blob:
            hits += 1

    if hits:
        score = min(1.0, 0.25 + hits * 0.18)
    else:
        score = 0.2
    return score


def filter_events_by_preferences(
    events: List[Dict[str, Any]],
    *,
    guest_text: str = "",
    guest_tags: Optional[Set[str]] = None,
    check_in: Optional[date] = None,
    check_out: Optional[date] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter and rank events by guest preferences, dates, and location."""
    text = _norm(guest_text)
    tag_set = guest_tags or set()
    family_pref = any(k in text for k in FAMILY_KEYWORDS) or bool(tag_set & {"family", "kids"})
    wine_pref = any(k in text for k in WINE_KEYWORDS) or "wine" in tag_set

    filtered: List[Dict[str, Any]] = []
    for ev in events:
        if family_pref:
            age = ev.get("age_group")
            tags = _event_tags(ev)
            if age not in ("family", "kids", "all_ages") and not (tags & {"family", "kids"}):
                continue
        if wine_pref:
            if ev.get("event_type") != "food_wine" and not (_event_tags(ev) & {"wine", "gastro"}):
                continue

        if check_in and check_out:
            start_raw = ev.get("start_at") or ev.get("start_date")
            if start_raw:
                try:
                    start_s = str(start_raw)[:10]
                    ev_date = date.fromisoformat(start_s)
                    if ev_date < check_in or ev_date > check_out:
                        continue
                except ValueError:
                    pass

        filtered.append(ev)

    if not filtered:
        filtered = list(events)

    def sort_key(ev: Dict[str, Any]) -> tuple:
        pref = preference_match_score(ev, guest_text, tag_set)
        start_raw = ev.get("start_at") or ev.get("start_date") or "9999"
        etype = ev.get("event_type") or "other"
        type_pri = EVENT_TYPE_PRIORITY.get(etype, 1)
        city_match = 0
        if city:
            ev_city = _norm(str(ev.get("city") or ""))
            if city.lower() in ev_city:
                city_match = 1
        return (-city_match, -pref, str(start_raw), -type_pri)

    filtered.sort(key=sort_key)
    return filtered


def normalize_event_type_value(value: Optional[str]) -> str:
    if value and value in EVENT_TYPES:
        return value
    return "other"
