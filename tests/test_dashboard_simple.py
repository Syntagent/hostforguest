"""
Simple dashboard test to verify endpoint structure and auth requirements.
"""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_realtime_updates_endpoint():
    """Test that realtime updates endpoint returns data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/realtime/updates")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_endpoints_require_auth():
    """Test that dashboard endpoints return 401 when unauthenticated."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        analytics_response = await client.get("/api/v1/hosts/analytics")
        assert analytics_response.status_code == 401

        groups_response = await client.get("/api/v1/guest-groups/host")
        assert groups_response.status_code == 401

        attractions_response = await client.get("/api/v1/attractions/host")
        assert attractions_response.status_code == 401
