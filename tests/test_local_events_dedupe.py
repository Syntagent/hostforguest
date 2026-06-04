"""Dedupe hashing for local events."""

from app.scraping.events.dedupe import event_content_hash, hash_draft
from app.scraping.events.schemas.local_event import LocalEventDraft


def test_same_url_same_hash():
    a = event_content_hash(title="Fest", url="https://tz-lovran.hr/x", start_iso="2026-10-10")
    b = event_content_hash(title="Fest", url="https://tz-lovran.hr/x", start_iso="2026-10-10")
    assert a == b


def test_hash_draft_stable():
    d = LocalEventDraft(title="Ab Fest", url="https://example.com", external_id="a1")
    assert hash_draft(d) == hash_draft(d)
