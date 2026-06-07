"""Google Places onboarding helpers use httpx, not the googlemaps SDK."""

from __future__ import annotations

import pytest

from app.api.v1 import host_onboarding_google as places

pytestmark = pytest.mark.no_db


@pytest.mark.asyncio
async def test_google_places_info_uses_text_search_http(monkeypatch):
    captured: dict = {}

    async def fake_get_json(url, params):
        captured["url"] = url
        captured["params"] = params
        return {
            "status": "OK",
            "results": [
                {
                    "place_id": "abc",
                    "name": "Lovran",
                    "rating": 4.8,
                    "types": ["locality"],
                    "vicinity": "Lovran",
                    "geometry": {"location": {"lat": 45.29, "lng": 14.27}},
                }
            ],
        }

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setattr(places, "_get_google_places_json", fake_get_json)

    result = await places.get_google_places_info("Lovran")

    assert result.success is True
    assert captured["url"] == places.GOOGLE_PLACES_TEXTSEARCH_URL
    assert captured["params"]["query"] == "Lovran"
    assert captured["params"]["key"] == "test-key"
    assert result.place_info and result.place_info.name == "Lovran"


@pytest.mark.asyncio
async def test_nearby_google_places_uses_nearby_http(monkeypatch):
    captured: dict = {}

    async def fake_get_json(url, params):
        captured["url"] = url
        captured["params"] = params
        return {
            "status": "OK",
            "results": [
                {
                    "place_id": "abc",
                    "name": "Park",
                    "rating": 4.6,
                    "types": ["tourist_attraction"],
                    "vicinity": "Lovran",
                    "geometry": {"location": {"lat": 45.29, "lng": 14.27}},
                }
            ],
        }

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setattr(places, "_get_google_places_json", fake_get_json)

    result = await places.get_nearby_google_places(45.29, 14.27, radius=1000)

    assert result["success"] is True
    assert captured["url"] == places.GOOGLE_PLACES_NEARBY_URL
    assert captured["params"]["location"] == "45.29,14.27"
    assert captured["params"]["radius"] == 1000
    assert result["nearby_places"][0]["name"] == "Park"
