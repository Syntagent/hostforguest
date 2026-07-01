"""Content hashing for event deduplication."""

from __future__ import annotations

import hashlib
from typing import Optional

from app.scraping.events.schemas.local_event import LocalEventDraft


def event_content_hash(
    *,
    title: str,
    url: Optional[str] = None,
    external_id: Optional[str] = None,
    start_iso: Optional[str] = None,
) -> str:
    key = "|".join(
        [
            (external_id or "").strip().lower(),
            (url or "").strip().lower(),
            title.strip().lower(),
            (start_iso or "").strip(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def hash_draft(draft: LocalEventDraft) -> str:
    start_iso = draft.start_at.isoformat() if draft.start_at else ""
    return event_content_hash(
        title=draft.title,
        url=draft.url,
        external_id=draft.external_id,
        start_iso=start_iso,
    )
