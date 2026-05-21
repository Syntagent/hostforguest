"""
Simple dashboard test to verify endpoint structure and auth requirements.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_realtime_updates_endpoint(async_client: AsyncClient):
    """Test that realtime updates endpoint returns data."""
    response = await async_client.get("/api/v1/realtime/updates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_endpoints_require_auth(async_client: AsyncClient):
    """Test that dashboard endpoints return 401 when unauthenticated."""
    analytics_response = await async_client.get("/api/v1/hosts/analytics")
    assert analytics_response.status_code == 401

    groups_response = await async_client.get("/api/v1/guest-groups/host")
    assert groups_response.status_code == 401

    attractions_response = await async_client.get("/api/v1/attractions/host")
    assert attractions_response.status_code == 401
