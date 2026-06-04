"""Event draft validation — chrome blocklist after LLM, not extraction."""

from app.scraping.events.filters import (
    filter_event_drafts,
    is_site_chrome_title,
    is_valid_event_draft_title,
)
from app.scraping.events.schemas.local_event import LocalEventDraft


def test_rejects_known_site_chrome():
    assert is_site_chrome_title("Otkrij destinaciju")
    assert is_site_chrome_title("Planirajte odmor")
    assert is_site_chrome_title("Dolazak automobilom")
    assert not is_site_chrome_title("51. Marunada")


def test_valid_event_titles():
    assert is_valid_event_draft_title("51. Marunada")
    assert not is_valid_event_draft_title("Tel")


def test_filter_event_drafts_drops_chrome_and_short():
    drafts = [
        LocalEventDraft(title="Marunada 2026", description="fest"),
        LocalEventDraft(title="Planirajte odmor", description="nav"),
        LocalEventDraft(title="ab", description="skip"),
    ]
    kept = filter_event_drafts(drafts)
    assert len(kept) == 1
    assert kept[0].title == "Marunada 2026"
