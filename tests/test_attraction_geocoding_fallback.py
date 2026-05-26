from app.services.attraction_service import AttractionService


def test_build_geocode_query_appends_croatia():
    query = AttractionService._build_geocode_query(
        address="Stari grad 12",
        city="Lovran",
    )
    assert query == "Stari grad 12, Lovran, Croatia"


def test_resolve_coordinates_prefers_existing_coordinates():
    service = AttractionService(db=None)
    lat, lng = service._resolve_coordinates(
        address="Korzo 5",
        city="Rijeka",
        latitude=45.3271,
        longitude=14.4422,
    )
    assert lat == 45.3271
    assert lng == 14.4422


def test_resolve_coordinates_treats_zero_zero_as_missing(monkeypatch):
    service = AttractionService(db=None)
    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_google",
        staticmethod(lambda query: None),
    )
    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_nominatim",
        staticmethod(lambda query: (45.2959, 14.2725)),
    )

    lat, lng = service._resolve_coordinates(
        address="Setaliste Marsala Tita 1",
        city="Opatija",
        latitude=0,
        longitude=0,
    )
    assert lat == 45.2959
    assert lng == 14.2725


def test_resolve_coordinates_falls_back_to_nominatim(monkeypatch):
    service = AttractionService(db=None)

    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_google",
        staticmethod(lambda query: None),
    )
    monkeypatch.setattr(
        AttractionService,
        "_geocode_with_nominatim",
        staticmethod(lambda query: (45.2959, 14.2725)),
    )

    lat, lng = service._resolve_coordinates(
        address="Setaliste Marsala Tita 1",
        city="Opatija",
        latitude=None,
        longitude=None,
    )
    assert lat == 45.2959
    assert lng == 14.2725
