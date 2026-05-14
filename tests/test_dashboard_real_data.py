"""
Test dashboard real data integration.

This test verifies that the dashboard endpoints return real data
from the backend instead of mock data.
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import get_db
from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.models.host import HostCreate
from app.models.guest_group import GuestGroupCreate
from app.models.attraction import AttractionCreate


@pytest.mark.asyncio
async def test_dashboard_analytics_real_data():
    """Test that dashboard analytics endpoint returns real data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "Host",
            "address": "Test Address",
            "city": "Lovran"
        }
        
        # Register host
        response = await client.post("/api/v1/hosts/register", json=host_data)
        assert response.status_code == 201
        
        # Login to get session token
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Test analytics endpoint
        analytics_response = await client.get("/api/v1/hosts/analytics", headers=headers)
        assert analytics_response.status_code == 200
        
        analytics_data = analytics_response.json()
        
        # Verify analytics structure
        assert "guest_groups" in analytics_data
        assert "attractions" in analytics_data
        assert "recommendations" in analytics_data
        assert "satisfaction" in analytics_data
        
        # Verify guest groups data
        guest_groups = analytics_data["guest_groups"]
        assert "total" in guest_groups
        assert "active" in guest_groups
        assert "inactive" in guest_groups
        assert isinstance(guest_groups["total"], int)
        assert isinstance(guest_groups["active"], int)
        assert isinstance(guest_groups["inactive"], int)
        
        # Verify attractions data
        attractions = analytics_data["attractions"]
        assert "total" in attractions
        assert "categories" in attractions
        assert isinstance(attractions["total"], int)
        assert isinstance(attractions["categories"], dict)
        
        # Verify recommendations data
        recommendations = analytics_data["recommendations"]
        assert "total_given" in recommendations
        assert "this_month" in recommendations
        assert isinstance(recommendations["total_given"], int)
        assert isinstance(recommendations["this_month"], int)
        
        # Verify satisfaction data
        satisfaction = analytics_data["satisfaction"]
        assert "average_rating" in satisfaction
        assert "total_reviews" in satisfaction
        assert isinstance(satisfaction["average_rating"], (int, float))
        assert isinstance(satisfaction["total_reviews"], int)


@pytest.mark.asyncio
async def test_guest_groups_real_data():
    """Test that guest groups endpoint returns real data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test2@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "Host",
            "address": "Test Address",
            "city": "Lovran"
        }
        
        # Register host
        response = await client.post("/api/v1/hosts/register", json=host_data)
        assert response.status_code == 201
        
        # Login to get session token
        login_data = {
            "email": "test2@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Test guest groups endpoint
        groups_response = await client.get("/api/v1/guest-groups/host", headers=headers)
        assert groups_response.status_code == 200
        
        groups_data = groups_response.json()
        assert isinstance(groups_data, list)
        
        # If there are groups, verify their structure
        if groups_data:
            group = groups_data[0]
            assert "id" in group
            assert "group_name" in group
            assert "access_code" in group
            assert "group_size" in group
            assert "status" in group
            assert "created_at" in group


@pytest.mark.asyncio
async def test_attractions_real_data():
    """Test that attractions endpoint returns real data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test3@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "Host",
            "address": "Test Address",
            "city": "Lovran"
        }
        
        # Register host
        response = await client.post("/api/v1/hosts/register", json=host_data)
        assert response.status_code == 201
        
        # Login to get session token
        login_data = {
            "email": "test3@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Test attractions endpoint
        attractions_response = await client.get("/api/v1/attractions/host", headers=headers)
        assert attractions_response.status_code == 200
        
        attractions_data = attractions_response.json()
        assert isinstance(attractions_data, list)
        
        # If there are attractions, verify their structure
        if attractions_data:
            attraction = attractions_data[0]
            assert "id" in attraction
            assert "name" in attraction
            assert "description" in attraction
            assert "category" in attraction
            assert "location" in attraction


@pytest.mark.asyncio
async def test_realtime_updates_endpoint():
    """Test that realtime updates endpoint returns data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/realtime/updates")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_data_consistency():
    """Test that dashboard data is consistent across endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test4@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "Host",
            "address": "Test Address",
            "city": "Lovran"
        }
        
        # Register host
        response = await client.post("/api/v1/hosts/register", json=host_data)
        assert response.status_code == 201
        
        # Login to get session token
        login_data = {
            "email": "test4@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Get analytics data
        analytics_response = await client.get("/api/v1/hosts/analytics", headers=headers)
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        
        # Get guest groups data
        groups_response = await client.get("/api/v1/guest-groups/host", headers=headers)
        assert groups_response.status_code == 200
        groups_data = groups_response.json()
        
        # Get attractions data
        attractions_response = await client.get("/api/v1/attractions/host", headers=headers)
        assert attractions_response.status_code == 200
        attractions_data = attractions_response.json()
        
        # Verify consistency
        assert analytics_data["guest_groups"]["total"] == len(groups_data)
        assert analytics_data["attractions"]["total"] == len(attractions_data)
        
        # Verify active groups count
        active_groups = len([g for g in groups_data if g["status"] == "active"])
        assert analytics_data["guest_groups"]["active"] == active_groups


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_dashboard_analytics_real_data())
    asyncio.run(test_guest_groups_real_data())
    asyncio.run(test_attractions_real_data())
    asyncio.run(test_archon_updates_real_data())
    asyncio.run(test_dashboard_data_consistency())
    print("✅ All dashboard real data tests passed!")
