"""Event recommendation performance helpers: cache, venue GPS, inferred stay window."""

from datetime import date, timedelta

import pytest

from app.services.event_geo_utils import resolve_city_coords as _resolve_city_coords
from app.services.event_recommendation_service import (
    EventCandidate,
    EventRecommendationService,
    GuestEventContext,
    _RECOMMENDATION_CACHE,
    CACHE_TTL_SEC,
)


@pytest.fixture(autouse=True)
def clear_recommendation_cache():
    _RECOMMENDATION_CACHE.clear()
    yield
    _RECOMMENDATION_CACHE.clear()


def test_min_distance_prefers_venue_coordinates():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Oprić",
        feed_cities=["Oprić", "Lovran"],
        broader_city="Lovran",
        region="Kvarner",
        stay_lat=45.273,
        stay_lng=14.274,
        check_in=date(2026, 6, 5),
        check_out=date(2026, 6, 12),
    )
    c = EventCandidate(
        id="v1",
        source="feed",
        title="Harbour concert",
        description="waterfront",
        search_blob="harbour concert waterfront",
        keywords=[],
        cities=["Opatija"],
        regions=[],
        url=None,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 8),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
        venue_lat=45.335,
        venue_lng=14.305,
        venue_name="Opatija waterfront",
    )
    dist = svc._min_distance_km(c, ctx)
    assert dist is not None
    assert dist < 15
    assert dist > 5


def test_plan_hint_short_trip_from_stay():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Oprić",
        feed_cities=["Oprić", "Lovran"],
        broader_city="Lovran",
        region="Kvarner",
        stay_lat=45.309,
        stay_lng=14.267,
        check_in=date(2026, 6, 5),
        check_out=date(2026, 6, 12),
    )
    c = EventCandidate(
        id="near",
        source="feed",
        title="Cherry festival",
        description="local",
        search_blob="festival",
        keywords=[],
        cities=["Lovran"],
        regions=[],
        url=None,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 8),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
        venue_lat=45.292,
        venue_lng=14.274,
        venue_name="Lovran",
    )
    hint = svc._plan_hint(c, ctx, 2.0)
    assert "Short trip from your stay" in hint
    assert "2.0 km" in hint


def test_build_context_infers_stay_window_when_dates_missing():
    svc = EventRecommendationService.__new__(EventRecommendationService)

    class FakeGroup:
        interests = ["food"]
        preferred_activities = []
        interested_regions = []
        budget_level = "moderate"
        travel_style = "balanced"
        check_in_date = None
        check_out_date = None
        typical_stay_duration = 5

    class FakeHost:
        typical_stay_duration = 7

    offerings = {
        "host_info": {"city": "Lovran", "broader_city": "Lovran"},
        "stay_info": {"city": "Oprić"},
        "location_info": {"region": "Kvarner", "coordinates": {"lat": 45.273, "lng": 14.274}},
    }
    ctx = svc._build_context(FakeGroup(), [], offerings, "Oprić", FakeHost(), None)
    assert ctx.inferred_stay_window is True
    assert ctx.check_in == date.today()
    assert ctx.check_out == ctx.check_in + timedelta(days=4)


def test_recommendation_cache_key_and_ttl():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    key = svc._cache_key("ABC123", date(2026, 6, 1), date(2026, 6, 10), 15, "food,wine")
    payload = {"success": True, "recommendations": []}
    _RECOMMENDATION_CACHE[key] = (1000.0, payload)

    cached = _RECOMMENDATION_CACHE.get(key)
    assert cached is not None
    assert cached[1]["success"] is True

    import time

    _RECOMMENDATION_CACHE[key] = (time.time() - CACHE_TTL_SEC - 1, payload)
    stale = _RECOMMENDATION_CACHE.get(key)
    assert stale is not None
    assert (time.time() - stale[0]) >= CACHE_TTL_SEC


def test_min_distance_uses_event_city_not_feed_city_at_stay():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Oprić",
        feed_cities=["Oprić", "Lovran"],
        broader_city="Lovran",
        region="Kvarner",
        stay_lat=45.273,
        stay_lng=14.274,
        check_in=date(2026, 6, 5),
        check_out=date(2026, 6, 12),
    )
    c = EventCandidate(
        id="lovran1",
        source="feed",
        title="Dani črešnja",
        description="festival",
        search_blob="cresnja festival",
        keywords=[],
        cities=["Lovran"],
        regions=[],
        url=None,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 8),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    dist = svc._min_distance_km(c, ctx)
    assert dist is not None
    assert 1.0 < dist < 5.0


def test_feed_row_backfills_city_coordinates():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    row = {
        "id": "x1",
        "title": "Opatija concert",
        "content": "music",
        "relevant_cities": ["Opatija"],
        "relevant_regions": [],
        "keywords": [],
        "start_at": "2026-07-10T18:00:00+00:00",
        "end_at": "2026-07-10T20:00:00+00:00",
    }
    candidate = svc._feed_row_to_candidate(row)
    assert candidate is not None
    assert candidate.venue_lat is not None
    assert candidate.venue_lng is not None


def test_resolve_city_coords_lovran():
    lat, lng = _resolve_city_coords("Lovran")
    assert lat is not None
    assert lng is not None
