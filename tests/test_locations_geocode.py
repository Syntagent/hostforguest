"""Public geocode endpoint resolves Croatian addresses."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_locations_geocode_opric_lovran(async_client: AsyncClient):
    res = await async_client.get(
        "/api/v1/locations/geocode",
        params={"address": "Oprić 71", "city": "Lovran", "county": "Primorsko-goranska"},
    )
    assert res.status_code == status.HTTP_200_OK, res.text
    body = res.json()
    assert 45.0 < body["lat"] < 46.0
    assert 14.0 < body["lng"] < 15.0
    assert body["precision"] in ("address", "approximate", "city")
    assert body["formatted_address"]
