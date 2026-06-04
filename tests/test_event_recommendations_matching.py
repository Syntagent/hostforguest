"""Event recommendation matching: interests, geography, and Croatian text."""

from datetime import date

from app.services.event_geo_utils import normalize_match_text as _normalize_match_text
from app.services.event_recommendation_service import (
    EventCandidate,
    EventRecommendationService,
    GuestEventContext,
)


def test_normalize_match_text_strips_croatian_diacritics():
    assert "cresnja" in _normalize_match_text("Dani črešnja va Lovrane")


def test_preference_score_food_guest_matches_cherry_festival():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Lovran",
        feed_cities=["Lovran", "Opatija"],
        broader_city="Lovran",
        region="Kvarner",
        stay_lat=45.273,
        stay_lng=14.274,
        check_in=date(2026, 6, 5),
        check_out=date(2026, 6, 12),
        keywords={"food", "wine"},
        interests={"food"},
    )
    c = EventCandidate(
        id="1",
        source="feed",
        title="Dani črešnja va Lovrane",
        description="Spring cherry events",
        search_blob=_normalize_match_text("Dani črešnja va Lovrane Spring cherry events"),
        keywords=["cherry"],
        cities=["Lovran"],
        regions=["Kvarner"],
        url=None,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    assert svc._preference_score(c, ctx) >= 0.5


def test_geographic_score_matches_feed_cities_not_only_stay_label():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Oprić",
        feed_cities=["Oprić", "Lovran", "Opatija"],
        broader_city="Lovran",
        region="Kvarner",
        stay_lat=45.273,
        stay_lng=14.274,
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 15),
    )
    c = EventCandidate(
        id="2",
        source="feed",
        title="Opatija concert",
        description="waterfront",
        search_blob="opatija concert waterfront",
        keywords=[],
        cities=["Opatija"],
        regions=[],
        url=None,
        start_date=date(2026, 7, 11),
        end_date=date(2026, 7, 11),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    assert svc._geographic_score(c, ctx) >= 0.9
