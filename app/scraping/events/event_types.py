"""Normalized event_type, age_group, and price enums for local events."""

from __future__ import annotations

from typing import List, Optional, Set

EVENT_TYPES: tuple[str, ...] = (
    "festival",
    "concert",
    "sports",
    "exhibition",
    "market",
    "workshop",
    "film",
    "kids",
    "cultural",
    "food_wine",
    "nature",
    "other",
)

AGE_GROUPS: tuple[str, ...] = ("all_ages", "family", "adults", "kids")
PRICE_VALUES: tuple[str, ...] = ("free", "paid", "unknown")
LANGUAGE_VALUES: tuple[str, ...] = ("hr", "en", "multi")

_EVENT_TYPE_ALIASES: dict[str, str] = {
    "food": "food_wine",
    "wine": "food_wine",
    "gastro": "food_wine",
    "gastronomy": "food_wine",
    "music": "concert",
    "culture": "cultural",
    "sport": "sports",
    "expo": "exhibition",
    "movie": "film",
    "cinema": "film",
    "children": "kids",
    "family_friendly": "kids",
    "outdoor": "nature",
    "hiking": "nature",
}

_AGE_GROUP_ALIASES: dict[str, str] = {
    "all": "all_ages",
    "everyone": "all_ages",
    "children": "kids",
    "child": "kids",
    "family_friendly": "family",
}

_PRICE_ALIASES: dict[str, str] = {
    "gratis": "free",
    "besplatno": "free",
    "donation": "paid",
    "ticket": "paid",
    "ulaznica": "paid",
}


def normalize_event_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if key in EVENT_TYPES:
        return key
    return _EVENT_TYPE_ALIASES.get(key, "other" if key else None)


def normalize_age_group(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower().replace(" ", "_")
    if key in AGE_GROUPS:
        return key
    return _AGE_GROUP_ALIASES.get(key)


def normalize_price(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower()
    if key in PRICE_VALUES:
        return key
    return _PRICE_ALIASES.get(key, "unknown")


def normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower()
    if key in LANGUAGE_VALUES:
        return key
    if key in ("croatian", "hrvatski"):
        return "hr"
    if key in ("english", "engleski"):
        return "en"
    return "hr"


def normalize_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    allowed = {
        "music", "wine", "gastro", "family", "kids", "outdoor", "indoor",
        "beach", "hiking", "art", "history", "folk", "dance", "film",
        "summer", "winter", "free", "paid", "evening", "morning",
    }
    out: List[str] = []
    seen: Set[str] = set()
    for raw in tags:
        t = str(raw).strip().lower()
        if not t or t in seen:
            continue
        if t in allowed:
            seen.add(t)
            out.append(t)
        elif t == "children":
            seen.add("kids")
            out.append("kids")
    return out[:12]
