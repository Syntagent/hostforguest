"""Guest stay city: address settlement vs profile city (e.g. Oprić in address, Lovran as city)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.host_offerings_for_guest import (
    align_guest_welcome_opening_line,
    build_host_offerings_payload,
    settlement_from_property_address,
    resolve_guest_stay_city,
)


@pytest.mark.parametrize(
    "address,expected",
    [
        ("71, 51415, Oprić, Croatia", "Oprić"),
        ("71, 51415, Oprić, Hrvatska", "Oprić"),
        ("51415 Oprić Croatia", "Oprić"),
        ("51415 Oprić, Croatia", "Oprić"),
        ("Building A\n51415 Oprić, Croatia", "Oprić"),
        ("71 Oprić", "Oprić"),
        ("Some street 1, 10000, Zagreb, Croatia", "Zagreb"),
        ("Only one line", "Only one line"),
        ("", None),
        (None, None),
    ],
)
def test_settlement_from_property_address(address, expected):
    assert settlement_from_property_address(address) == expected


def test_resolve_guest_stay_ignores_placeholder_profile_address_uses_host_line():
    """Migrations may set host_profiles.address NOT NULL to 'Address not specified'."""
    host = SimpleNamespace(
        first_name="Test",
        last_name="Host",
        city="Rijeka",
        address="71, 51415, Oprić, Croatia",
        county=None,
        latitude=None,
        longitude=None,
        languages=["hr", "en"],
        local_specialties=[],
        business_type="apartment",
        max_group_size=12,
        typical_stay_duration=7,
        welcome_message=None,
        local_tips=[],
    )
    profile = SimpleNamespace(
        address="Address not specified",
        city="Lovran",
        county=None,
        latitude=None,
        longitude=None,
        property_name="Sunrise Heights Lovran",
        amenities=[],
        max_guests=6,
        favorite_local_spots=[],
        expertise_areas=[],
        updated_at=None,
        location_story=None,
        guest_testimonials=[],
    )
    assert resolve_guest_stay_city(host, profile) == "Oprić"
    payload = build_host_offerings_payload(host, profile, "CODE")
    assert payload["stay_info"]["city"] == "Oprić"
    assert "Oprić" in (payload["stay_info"]["address"] or "")


def test_resolve_guest_stay_from_structured_host_address_when_profile_address_empty():
    """Host.address may hold the property line if profile.address was never filled."""
    host = SimpleNamespace(
        first_name="Test",
        last_name="Host",
        city="Rijeka",
        address="51415 Oprić, Croatia",
        county=None,
        latitude=None,
        longitude=None,
        languages=["hr", "en"],
        local_specialties=[],
        business_type="apartment",
        max_group_size=12,
        typical_stay_duration=7,
        welcome_message=None,
        local_tips=[],
    )
    profile = SimpleNamespace(
        address=None,
        city="Lovran",
        county=None,
        latitude=None,
        longitude=None,
        property_name="Villa",
        amenities=[],
        max_guests=4,
        favorite_local_spots=[],
        expertise_areas=[],
        updated_at=None,
        location_story=None,
        guest_testimonials=[],
    )
    assert resolve_guest_stay_city(host, profile) == "Oprić"


def test_resolve_guest_stay_prefers_address_settlement_over_profile_city():
    host = SimpleNamespace(
        first_name="Test",
        last_name="Host",
        city="Rijeka",
        address="Host street 1",
        county=None,
        latitude=None,
        longitude=None,
        languages=["hr", "en"],
        local_specialties=[],
        business_type="apartment",
        max_group_size=12,
        typical_stay_duration=7,
        welcome_message=None,
        local_tips=[],
    )
    profile = SimpleNamespace(
        address="71, 51415, Oprić, Croatia",
        city="Lovran",
        county="Primorje-Gorski Kotar County",
        latitude=45.311,
        longitude=14.2705,
        property_name="Sunrise Heights Lovran",
        amenities=["wifi"],
        max_guests=6,
        favorite_local_spots=[],
        expertise_areas=[],
        updated_at=None,
        location_story=None,
        guest_testimonials=[],
    )
    assert resolve_guest_stay_city(host, profile) == "Oprić"

    payload = build_host_offerings_payload(host, profile, "ABC123")
    assert payload["stay_info"]["city"] == "Oprić"
    assert payload["host_info"]["broader_city"] == "Lovran"
    assert "Oprić" in payload["stay_info"]["address"]


def test_resolve_guest_stay_from_location_story_postal():
    host = SimpleNamespace(
        first_name="Test",
        last_name="Host",
        city="Rijeka",
        address="Rijeka HQ",
        county=None,
        latitude=None,
        longitude=None,
        languages=["en"],
        local_specialties=[],
        business_type="apartment",
        max_group_size=8,
        typical_stay_duration=7,
        welcome_message=None,
        description=None,
        local_tips=[],
    )
    profile = SimpleNamespace(
        address=None,
        city="Rijeka",
        county=None,
        latitude=None,
        longitude=None,
        property_name="Novasol 3",
        amenities=[],
        max_guests=4,
        favorite_local_spots=[],
        expertise_areas=[],
        updated_at=None,
        location_story="Quiet spot near the sea.\n51415 Oprić, Croatia",
        guest_testimonials=[],
    )
    assert resolve_guest_stay_city(host, profile) == "Oprić"


def test_align_guest_welcome_replaces_host_city_with_stay_city():
    assert (
        align_guest_welcome_opening_line(
            "Welcome to Rijeka!\nOur apartment is lovely.",
            stay_city="Oprić",
            host_city="Rijeka",
        )
        == "Welcome to Oprić!\nOur apartment is lovely."
    )


def test_build_payload_aligns_welcome_when_address_has_settlement():
    host = SimpleNamespace(
        first_name="Benedikt",
        last_name="Perak",
        city="Rijeka",
        address="Rijeka",
        county=None,
        latitude=None,
        longitude=None,
        languages=["en", "hr"],
        local_specialties=[],
        business_type="apartment",
        max_group_size=8,
        typical_stay_duration=7,
        welcome_message="Welcome to Rijeka!\nLine two.",
        description=None,
        local_tips=[],
    )
    profile = SimpleNamespace(
        address="71, 51415, Oprić, Croatia",
        city="Lovran",
        county="Primorje-Gorski Kotar County",
        latitude=45.3,
        longitude=14.27,
        property_name="Novasol 3",
        amenities=[],
        max_guests=4,
        favorite_local_spots=[],
        expertise_areas=[],
        updated_at=None,
        location_story=None,
        guest_testimonials=[],
    )
    payload = build_host_offerings_payload(host, profile, "XGQK6GZC")
    assert payload["stay_info"]["city"] == "Oprić"
    assert payload["host_info"]["welcome_message"].startswith("Welcome to Oprić!")
