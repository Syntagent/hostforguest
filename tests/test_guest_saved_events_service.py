"""Guest saved events storage helpers."""

from app.services.guest_saved_events_service import _load_store, _merge_seasonal, SAVED_EVENTS_KEY


def test_load_store_empty():
    assert _load_store(None) == {}
    assert _load_store({}) == {}


def test_merge_seasonal_preserves_other_keys():
    merged = _merge_seasonal({"summer": "beach"}, {"e1": {"event_id": "e1", "title": "Fest"}})
    assert merged["summer"] == "beach"
    assert SAVED_EVENTS_KEY in merged
    assert merged[SAVED_EVENTS_KEY]["by_id"]["e1"]["title"] == "Fest"
