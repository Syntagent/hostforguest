"""
Tests for route templates and itinerary Pydantic rules (no HTTP fixtures required).
"""

from datetime import date
import uuid

import pytest

from app.models.itinerary import ItineraryCreate, ItinerarySuggestionRequest


def test_itinerary_create_template_allows_no_dates():
    m = ItineraryCreate(title="Day in Lovran", base_location="Lovran, Croatia", is_template=True)
    assert m.is_template is True
    assert m.start_date is None
    assert m.end_date is None


def test_itinerary_create_guest_requires_dates():
    with pytest.raises(ValueError, match="start_date"):
        ItineraryCreate(
            title="Trip",
            base_location="Lovran",
            is_template=False,
        )


def test_itinerary_create_guest_with_dates_ok():
    m = ItineraryCreate(
        title="Trip",
        base_location="Lovran",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 3),
        is_template=False,
    )
    assert m.is_template is False


def test_suggestion_request_guest_group_optional():
    r = ItinerarySuggestionRequest(
        duration_days=2,
        guest_group_id=None,
        theme_prompt="Culinary tour",
    )
    assert r.guest_group_id is None
    assert r.theme_prompt == "Culinary tour"


def test_suggestion_request_with_guest_group():
    gid = uuid.uuid4()
    r = ItinerarySuggestionRequest(duration_days=1, guest_group_id=gid)
    assert r.guest_group_id == gid
