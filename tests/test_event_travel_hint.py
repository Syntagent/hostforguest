"""Road travel hint helper for event plan copy."""

import os

from app.services.event_travel_hint import road_travel_hint


def test_road_travel_hint_without_api_key_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    from app.services import event_travel_hint as mod

    mod._CACHE.clear()
    assert mod.road_travel_hint(45.3, 14.27, 45.29, 14.27, 2.0) is None


def test_road_travel_hint_skips_far_events():
    assert road_travel_hint(45.3, 14.27, 45.8, 15.0, 30.0) is None
