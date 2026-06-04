"""Event recommendation timing scores respect stay window."""

from datetime import date, timedelta

from app.services.event_recommendation_service import EventCandidate, EventRecommendationService, GuestEventContext


def test_timing_score_outside_stay_is_low():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Lovran",
        feed_cities=["Lovran"],
        broader_city=None,
        region="Kvarner",
        stay_lat=45.168,
        stay_lng=14.274,
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 10),
    )
    c = EventCandidate(
        id="1",
        source="feed",
        title="Winter ski",
        description="snow",
        search_blob="winter ski snow",
        keywords=[],
        cities=["Zagreb"],
        regions=[],
        url=None,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 5),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    assert svc._timing_score(c, ctx) < 0.3


def test_timing_score_inside_stay_is_high():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Lovran",
        feed_cities=["Lovran"],
        broader_city=None,
        region="Kvarner",
        stay_lat=45.168,
        stay_lng=14.274,
        check_in=date(2026, 10, 1),
        check_out=date(2026, 10, 15),
    )
    c = EventCandidate(
        id="2",
        source="feed",
        title="Marunada",
        description="festival",
        search_blob="marunada festival",
        keywords=["festival"],
        cities=["Lovran"],
        regions=["Kvarner"],
        url=None,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    assert svc._timing_score(c, ctx) >= 0.85


def test_timing_score_near_stay_before_check_in():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Lovran",
        feed_cities=["Lovran"],
        broader_city=None,
        region="Kvarner",
        stay_lat=45.168,
        stay_lng=14.274,
        check_in=date(2026, 6, 5),
        check_out=date(2026, 6, 12),
    )
    c = EventCandidate(
        id="4",
        source="feed",
        title="Wine Day",
        description="tasting",
        search_blob="wine day tasting",
        keywords=["wine"],
        cities=["Lovran"],
        regions=["Kvarner"],
        url=None,
        start_date=date(2026, 5, 31),
        end_date=date(2026, 5, 31),
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    score = svc._timing_score(c, ctx)
    assert 0.65 <= score <= 0.75


def test_timing_score_undated_is_low():
    svc = EventRecommendationService.__new__(EventRecommendationService)
    ctx = GuestEventContext(
        stay_city="Lovran",
        feed_cities=["Lovran"],
        broader_city=None,
        region="Kvarner",
        stay_lat=45.168,
        stay_lng=14.274,
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 10),
    )
    c = EventCandidate(
        id="3",
        source="feed",
        title="Mystery event",
        description="no date",
        search_blob="mystery event",
        keywords=[],
        cities=["Lovran"],
        regions=[],
        url=None,
        start_date=None,
        end_date=None,
        event_type="events",
        booking_required=False,
        admission_info=None,
        host_curated=False,
    )
    assert svc._timing_score(c, ctx) <= 0.3
