import pytest

from app.services.attraction_service import AttractionService


def test_ensure_coordinates_returns_existing_coordinates():
    service = AttractionService(db=None)
    lat, lng = service._ensure_coordinates(
        address="Old Town",
        city="Lovran",
        latitude=45.2917,
        longitude=14.2762,
    )
    assert lat == 45.2917
    assert lng == 14.2762


def test_ensure_coordinates_raises_when_unresolvable(monkeypatch):
    service = AttractionService(db=None)

    monkeypatch.setattr(
        service,
        "_resolve_coordinates",
        lambda address, city, latitude, longitude: (None, None),
    )

    with pytest.raises(ValueError, match="requires geolocation"):
        service._ensure_coordinates(
            address="Unknown place",
            city="Unknown city",
            latitude=None,
            longitude=None,
        )
