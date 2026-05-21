"""
Test dashboard endpoints for the TouristGuideLocal platform.

Tests the host dashboard API endpoints including profile retrieval
and analytics data.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

import uuid


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


def _host_body(email: str) -> dict:
    return {
        "email": email,
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "Host",
        "phone": "+38551111222",
        "business_name": "Dash Test Biz",
        "business_type": "apartment",
        "address": "Dash Test St 1",
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "postal_code": "51450",
        "country": "Croatia",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "local_specialties": ["seafood"],
        "languages": ["hr", "en"],
        "max_group_size": 6,
        "description": "Host for dashboard tests",
        "welcome_message": "Welcome",
    }


@pytest.mark.asyncio
async def test_get_host_profile_endpoint(async_client: AsyncClient):
    """GET /api/v1/hosts/me/profile — same DB as HTTP (register via API)."""
    email = f"dash-prof-{uuid.uuid4().hex[:12]}@example.com"
    r = await async_client.post("/api/v1/hosts/register", json=_host_body(email))
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["session_token"]

    response = await async_client.get(
        "/api/v1/hosts/me/profile",
        headers={"X-Session-Token": token},
    )

    assert response.status_code == 200
    assert response.json().get("host_id")


@pytest.mark.asyncio
async def test_get_host_analytics_endpoint(async_client: AsyncClient):
    """Test the GET /api/v1/hosts/analytics endpoint."""
    email = f"dash-analytics-{uuid.uuid4().hex[:12]}@example.com"
    r = await async_client.post("/api/v1/hosts/register", json=_host_body(email))
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    session_token = login.json()["session_token"]
    
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
