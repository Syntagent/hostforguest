"""Geography helpers for Lovran / Oprić event distances."""

from app.services.event_geo_utils import (
    coords_match_stale_centroid,
    resolve_city_coords,
    same_municipality,
)
from app.services.event_recommendation_service import (
    EventCandidate,
    EventRecommendationService,
    GuestEventContext,
)
from app.services.maintenance_service import haversine_km
from datetime import date


def test_lovran_centroid_is_near_opric_stay_not_11km():
    stay_lat, stay_lng = 45.273, 14.274  # Ben profile — Oprić address
    lovran_lat, lovran_lng = resolve_city_coords("Lovran")
    assert lovran_lat is not None and lovran_lng is not None
    dist = haversine_km(stay_lat, stay_lng, lovran_lat, lovran_lng)
    assert dist < 5.0
    assert dist > 1.0


def test_stale_lovran_centroid_detected():
    assert coords_match_stale_centroid("Lovran", 45.168, 14.274)
    assert not coords_match_stale_centroid("Lovran", 45.292, 14.276)


def test_opric_and_lovran_same_municipality():
    assert same_municipality("Oprić", "Lovran")
    assert same_municipality("Liganj", "Oprić")


def test_lovran_event_distance_from_opric_stay():
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
        title="Dani črešnja va Lovrane",
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
        venue_lat=45.292,
        venue_lng=14.276,
    )
    dist = svc._min_distance_km(c, ctx)
    assert dist is not None
    assert dist < 5.0
    assert dist > 1.0
