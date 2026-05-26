"""Geocoding service tests."""

from app.services.geocoding_service import GeocodingService
from app.services.attraction_service import AttractionService


def test_query_candidates_prefers_full_address():
    queries = GeocodingService._query_candidates(
        address="Oprić 71",
        city="Lovran",
        county="Primorsko-goranska",
    )
    assert queries[0][0] == "Oprić 71, Lovran, Primorsko-goranska, Croatia"
    assert queries[0][1] == "address"


def test_geocode_falls_back_to_city(monkeypatch):
    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_google",
        staticmethod(lambda query: None),
    )

    def fake_nominatim(query: str):
        if query == "Lovran, Croatia":
            return 45.2916807, 14.2762597
        return None

    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_nominatim",
        staticmethod(fake_nominatim),
    )

    result = GeocodingService.geocode(
        address="Unknown street 999",
        city="Lovran",
        county="Primorsko-goranska",
    )
    assert result is not None
    assert result.precision == "city"
    assert abs(result.latitude - 45.2916807) < 0.001
