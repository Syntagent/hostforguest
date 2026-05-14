"""
Test dashboard endpoints for the TouristGuideLocal platform.

Tests the host dashboard API endpoints including profile retrieval
and analytics data.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.models.host import Host, HostCreate


def test_dashboard_endpoints_require_authentication_sync(client: TestClient):
    """Test that dashboard endpoints require authentication using sync client."""
    
    # Test profile endpoint without authentication
    response = client.get("/api/v1/hosts/me/profile")
    assert response.status_code == 401
    assert "Session token required" in response.json()["detail"]
    
    # Test analytics endpoint without authentication
    response = client.get("/api/v1/hosts/analytics")
    assert response.status_code == 401
    assert "Session token required" in response.json()["detail"]


def test_dashboard_endpoints_invalid_session_sync(client: TestClient):
    """Test dashboard endpoints with invalid session token using sync client."""
    
    # Test profile endpoint with invalid token
    response = client.get(
        "/api/v1/hosts/me/profile",
        headers={"X-Session-Token": "invalid-token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]
    
    # Test analytics endpoint with invalid token
    response = client.get(
        "/api/v1/hosts/analytics",
        headers={"X-Session-Token": "invalid-token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_host_profile_endpoint(async_client: AsyncClient, async_db_session: Session):
    """Test the GET /api/v1/hosts/me/profile endpoint."""
    
    # Create a test host
    host_service = HostService(async_db_session)
    host_data = HostCreate(
        email="test@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="Host"
    )
    host = await host_service.create_host(host_data)
    
    # Create a session for the host
    session_service = SessionService(async_db_session)
    session_token = await session_service.create_session(host.id)
    
    # Test the profile endpoint
    response = await async_client.get(
        "/api/v1/hosts/me/profile",
        headers={"X-Session-Token": session_token}
    )
    
    # Should return 404 since no profile exists yet
    assert response.status_code == 404
    assert "Host profile not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_host_analytics_endpoint(async_client: AsyncClient, async_db_session: Session):
    """Test the GET /api/v1/hosts/analytics endpoint."""
    
    # Create a test host
    host_service = HostService(async_db_session)
    host_data = HostCreate(
        email="analytics@example.com",
        password="testpassword123",
        first_name="Analytics",
        last_name="Test",
        address="Test Address",
        city="Lovran"
    )
    host = await host_service.create_host(host_data)
    
    # Create a session for the host
    session_service = SessionService(async_db_session)
    session_data = await session_service.create_session(host.id)
    session_token = session_data["session_token"]
    
    # Test the analytics endpoint
    response = await async_client.get(
        "/api/v1/hosts/analytics",
        headers={"X-Session-Token": session_token}
    )
    
    # Should return 200 with analytics data
    assert response.status_code == 200
    data = response.json()
    
    # Check that analytics structure is correct
    assert "guest_groups" in data
    assert "attractions" in data
    assert "recommendations" in data
    assert "satisfaction" in data
    
    # Check guest groups structure
    assert "total" in data["guest_groups"]
    assert "active" in data["guest_groups"]
    assert "inactive" in data["guest_groups"]
    
    # Check attractions structure
    assert "total" in data["attractions"]
    assert "categories" in data["attractions"]
    
    # Check recommendations structure
    assert "total_given" in data["recommendations"]
    assert "this_month" in data["recommendations"]
    
    # Check satisfaction structure
    assert "average_rating" in data["satisfaction"]
    assert "total_reviews" in data["satisfaction"]


@pytest.mark.asyncio
async def test_dashboard_endpoints_require_authentication(async_client: AsyncClient):
    """Test that dashboard endpoints require authentication."""
    
    # Test profile endpoint without authentication
    response = await async_client.get("/api/v1/hosts/me/profile")
    assert response.status_code == 401
    assert "Session token required" in response.json()["detail"]
    
    # Test analytics endpoint without authentication
    response = await async_client.get("/api/v1/hosts/analytics")
    assert response.status_code == 401
    assert "Session token required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dashboard_endpoints_invalid_session(async_client: AsyncClient):
    """Test dashboard endpoints with invalid session token."""
    
    # Test profile endpoint with invalid token
    response = await async_client.get(
        "/api/v1/hosts/me/profile",
        headers={"X-Session-Token": "invalid-token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]
    
    # Test analytics endpoint with invalid token
    response = await async_client.get(
        "/api/v1/hosts/analytics",
        headers={"X-Session-Token": "invalid-token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]
