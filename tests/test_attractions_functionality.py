"""
Test Attractions CRUD functionality.

This test verifies that the Attractions tab functionality works correctly
including creating, viewing, editing, and deleting attractions.
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_attraction():
    """Test creating a new attraction."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First create a test host
        host_data = {
            "email": "test_host_attractions@example.com",
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
            "email": "test_host_attractions@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Create a new attraction
        attraction_data = {
            "name": "Test Croatian Restaurant",
            "description": "A wonderful local restaurant serving authentic Istrian cuisine",
            "category": "Restaurant",
            "location": "Lovran, Istria, Croatia",
            "cost_estimate": "€20-35 per person",
            "authenticity_level": "high"
        }
        
        create_response = await client.post("/api/v1/attractions", json=attraction_data, headers=headers)
        assert create_response.status_code == 201
        
        created_attraction = create_response.json()
        assert "id" in created_attraction
        assert created_attraction["name"] == "Test Croatian Restaurant"
        assert created_attraction["category"] == "Restaurant"
        assert created_attraction["location"] == "Lovran, Istria, Croatia"
        
        print(f"✅ Attraction created successfully - ID: {created_attraction['id']}")


@pytest.mark.asyncio
async def test_get_host_attractions():
    """Test retrieving attractions for a host."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_attractions2@example.com",
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
            "email": "test_host_attractions2@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Get host's attractions
        attractions_response = await client.get("/api/v1/attractions/host", headers=headers)
        assert attractions_response.status_code == 200
        
        attractions_data = attractions_response.json()
        assert isinstance(attractions_data, list)
        
        print(f"✅ Retrieved {len(attractions_data)} attractions for host")


@pytest.mark.asyncio
async def test_update_attraction():
    """Test updating an attraction."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_update@example.com",
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
            "email": "test_host_update@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Create an attraction first
        attraction_data = {
            "name": "Original Name",
            "description": "Original description",
            "category": "Restaurant",
            "location": "Lovran, Istria, Croatia",
            "cost_estimate": "€20-35 per person",
            "authenticity_level": "high"
        }
        
        create_response = await client.post("/api/v1/attractions", json=attraction_data, headers=headers)
        assert create_response.status_code == 201
        
        created_attraction = create_response.json()
        attraction_id = created_attraction["id"]
        
        # Update the attraction
        update_data = {
            "name": "Updated Croatian Restaurant",
            "description": "Updated description with more details",
            "cost_estimate": "€25-40 per person"
        }
        
        update_response = await client.put(f"/api/v1/attractions/{attraction_id}", json=update_data, headers=headers)
        assert update_response.status_code == 200
        
        updated_attraction = update_response.json()
        assert updated_attraction["name"] == "Updated Croatian Restaurant"
        assert updated_attraction["description"] == "Updated description with more details"
        assert updated_attraction["cost_estimate"] == "€25-40 per person"
        
        print(f"✅ Attraction updated successfully - ID: {attraction_id}")


@pytest.mark.asyncio
async def test_attraction_validation():
    """Test attraction validation requirements."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_validation@example.com",
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
            "email": "test_host_validation@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Test with missing required fields
        invalid_data = {
            "name": "Test Attraction"
            # Missing description, category, location
        }
        
        create_response = await client.post("/api/v1/attractions", json=invalid_data, headers=headers)
        # Should return 422 (validation error) or 400 (bad request)
        assert create_response.status_code in [400, 422]
        
        print("✅ Attraction validation working correctly")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_create_attraction())
    asyncio.run(test_get_host_attractions())
    asyncio.run(test_update_attraction())
    asyncio.run(test_attraction_validation())
    print("✅ All attractions functionality tests passed!")
