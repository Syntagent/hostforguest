"""
Booking.com HTTP client: mock mode, reservation fetch shape.
"""

import os

import pytest

from app.integrations.booking_com.client import BookingComClient


@pytest.mark.asyncio
async def test_booking_com_client_mock_returns_normalized_fetch():
    os.environ["BOOKING_COM_MOCK"] = "true"
    client = BookingComClient("user", "pass")
    rows, _cursor = await client.fetch_reservations("hotel-123", None)
    assert len(rows) >= 1
    assert rows[0].get("external_reservation_id")


@pytest.mark.asyncio
async def test_booking_com_client_missing_credentials_uses_mock():
    os.environ["BOOKING_COM_MOCK"] = ""
    client = BookingComClient("", "")
    assert client._mock is True
    ok = await client.push_availability({"hotel_id": "1", "room_id": "r"})
    assert ok is True
