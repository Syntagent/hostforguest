"""Shared listing-page parsing helpers."""

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scraping.events.filters import is_valid_event_draft_title
from app.scraping.events.normalizer import infer_tags, parse_hr_date_range
from app.scraping.events.schemas.local_event import LocalEventDraft


def parse_article_cards(
    html: str,
    *,
    base_url: str,
    item_selector: str,
    title_selector: str = "h2, h3, .title, a",
    date_selector: str = ".date, time, .event-date, .datum",
    desc_selector: str = "p, .description, .excerpt",
    link_selector: str = "a[href]",
    default_city: Optional[str] = None,
    default_region: Optional[str] = None,
) -> List[LocalEventDraft]:
    soup = BeautifulSoup(html, "html.parser")
    drafts: List[LocalEventDraft] = []
    seen_titles: set[str] = set()

    for el in soup.select(item_selector):
        title_el = el.select_one(title_selector)
        title = (title_el.get_text(strip=True) if title_el else "").strip()
        if not is_valid_event_draft_title(title):
            continue
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)

        date_el = el.select_one(date_selector)
        date_text = date_el.get_text(" ", strip=True) if date_el else ""
        if date_el and date_el.get("datetime"):
            date_text = f"{date_text} {date_el['datetime']}"
        start_at, end_at = parse_hr_date_range(date_text)

        desc_parts = [
            p.get_text(" ", strip=True)
            for p in el.select(desc_selector)[:2]
            if p.get_text(strip=True)
        ]
        description = " ".join(desc_parts)[:2000] if desc_parts else title

        url = None
        link = el.select_one(link_selector)
        if link and link.get("href"):
            href = link["href"]
            if not href.startswith("#"):
                url = urljoin(base_url, href)

        blob = f"{title} {description} {date_text}"
        drafts.append(
            LocalEventDraft(
                title=title[:500],
                description=description,
                url=url,
                start_at=start_at,
                end_at=end_at or start_at,
                city=default_city,
                region=default_region,
                tags=infer_tags(blob),
                external_id=_slug_id(url or title),
                confidence=0.8 if start_at else 0.55,
            )
        )
    return drafts


def _slug_id(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:120] or "event"
