"""Validation for event drafts after LLM/ingestion (not a replacement for model extraction)."""

from __future__ import annotations

import re

# Known tourism-site navigation / travel-info headings (legacy selector scrape noise).
# Used only to reject rows — not to discover events.
_SITE_CHROME_RE = re.compile(
    r"^(?:"
    r"tel\.?|e-?mail|adresa|više|more|kontakt|"
    r"smještaj|newsletter|prijava|login|o\s+nama|naslovnica|"
    r"opširnije|opcirije|više\s+o|read\s+more"
    r")$|"
    r"(?:"
    r"otkrij\s+destinacij|planirajte\s+odmor|"
    r"dolazak\s+autom|dolazak\s+vlak|dolazak\s+avion|dolazak\s+autobus|"
    r"kako\s+doći|radno\s+vrijeme|cookie|privatnost|"
    r"prirodni\s+položaj|destinacija\s+bogate"
    r")",
    re.IGNORECASE,
)


def is_site_chrome_title(title: str) -> bool:
    """True if title is known site chrome, not a public event."""
    t = (title or "").strip()
    if not t:
        return True
    return bool(_SITE_CHROME_RE.search(t))


def is_valid_event_draft_title(title: str) -> bool:
    t = (title or "").strip()
    if len(t) < 4 or len(t) > 500:
        return False
    return not is_site_chrome_title(t)


def filter_event_drafts(drafts: list) -> list:
    return [d for d in drafts if is_valid_event_draft_title(getattr(d, "title", ""))]


def scrape_quality_score(drafts: list) -> float:
    if not drafts:
        return 0.0
    good = 0
    for d in drafts:
        if not is_valid_event_draft_title(getattr(d, "title", "")):
            continue
        has_date = bool(getattr(d, "start_at", None))
        if has_date or getattr(d, "confidence", 0) >= 0.7:
            good += 1
        else:
            good += 0.5
    return good / len(drafts)
