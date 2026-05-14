"""
Test Guest Groups CRUD functionality.

This test verifies that the Guest Groups tab functionality works correctly
including creating, viewing, and managing guest groups.
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_guest_group():
    """Test creating a new guest group."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First create a test host
        host_data = {
            "email": "test_host_groups@example.com",
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
            "email": "test_host_groups@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Create a new guest group
        group_data = {
            "group_name": "Test Family Group",
            "group_size": 4,
            "preferences": [
                {
                    "guest_name": "John Smith",
                    "age_range": "adult",
                    "interests": ["history", "food"],
                    "mobility_level": "high",
                    "budget_level": "medium",
                    "language_preference": "en"
                },
                {
                    "guest_name": "Jane Smith",
                    "age_range": "adult",
                    "interests": ["art", "nature"],
                    "mobility_level": "medium",
                    "budget_level": "medium",
                    "language_preference": "en"
                }
            ]
        }
        
        create_response = await client.post("/api/v1/guest-groups", json=group_data, headers=headers)
        assert create_response.status_code == 201
        
        created_group = create_response.json()
        assert "id" in created_group
        assert created_group["group_name"] == "Test Family Group"
        assert created_group["group_size"] == 4
        assert len(created_group["preferences"]) == 2
        assert "access_code" in created_group
        
        print(f"✅ Guest group created successfully - ID: {created_group['id']}, Access Code: {created_group['access_code']}")


@pytest.mark.asyncio
async def test_get_host_guest_groups():
    """Test retrieving guest groups for a host."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_groups2@example.com",
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
            "email": "test_host_groups2@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Get host's guest groups
        groups_response = await client.get("/api/v1/guest-groups/host", headers=headers)
        assert groups_response.status_code == 200
        
        groups_data = groups_response.json()
        assert isinstance(groups_data, list)
        
        print(f"✅ Retrieved {len(groups_data)} guest groups for host")


@pytest.mark.asyncio
async def test_guest_group_access_code_generation():
    """Test that access codes are generated correctly."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_access@example.com",
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
            "email": "test_host_access@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Create multiple groups to test access code uniqueness
        group_data = {
            "group_name": "Access Code Test Group",
            "group_size": 2,
            "preferences": []
        }
        
        access_codes = []
        for i in range(3):
            group_data["group_name"] = f"Access Code Test Group {i+1}"
            create_response = await client.post("/api/v1/guest-groups", json=group_data, headers=headers)
            assert create_response.status_code == 201
            
            created_group = create_response.json()
            access_code = created_group["access_code"]
            access_codes.append(access_code)
            
            # Verify access code format (should be alphanumeric)
            assert len(access_code) >= 6
            assert access_code.isalnum()
        
        # Verify all access codes are unique
        assert len(set(access_codes)) == 3
        
        print(f"✅ Access codes generated successfully: {access_codes}")


@pytest.mark.asyncio
async def test_guest_group_preferences():
    """Test guest group preferences functionality."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test host
        host_data = {
            "email": "test_host_prefs@example.com",
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
            "email": "test_host_prefs@example.com",
            "password": "testpassword123"
        }
        login_response = await client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        session_token = login_response.json()["session_token"]
        headers = {"X-Session-Token": session_token}
        
        # Create group with detailed preferences
        group_data = {
            "group_name": "Preferences Test Group",
            "group_size": 3,
            "preferences": [
                {
                    "guest_name": "Alice Johnson",
                    "age_range": "adult",
                    "interests": ["history", "architecture", "local_cuisine"],
                    "mobility_level": "high",
                    "budget_level": "high",
                    "language_preference": "en"
                },
                {
                    "guest_name": "Bob Johnson",
                    "age_range": "senior",
                    "interests": ["nature", "photography"],
                    "mobility_level": "medium",
                    "budget_level": "medium",
                    "language_preference": "en"
                },
                {
                    "guest_name": "Charlie Johnson",
                    "age_range": "child",
                    "interests": ["beach", "ice_cream"],
                    "mobility_level": "high",
                    "budget_level": "low",
                    "language_preference": "en"
                }
            ]
        }
        
        create_response = await client.post("/api/v1/guest-groups", json=group_data, headers=headers)
        assert create_response.status_code == 201
        
        created_group = create_response.json()
        assert len(created_group["preferences"]) == 3
        
        # Verify preference details
        alice_pref = created_group["preferences"][0]
        assert alice_pref["guest_name"] == "Alice Johnson"
        assert alice_pref["age_range"] == "adult"
        assert "history" in alice_pref["interests"]
        assert alice_pref["mobility_level"] == "high"
        assert alice_pref["budget_level"] == "high"
        
        print(f"✅ Guest group preferences saved correctly for {len(created_group['preferences'])} guests")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_create_guest_group())
    asyncio.run(test_get_host_guest_groups())
    asyncio.run(test_guest_group_access_code_generation())
    asyncio.run(test_guest_group_preferences())
    print("✅ All guest groups functionality tests passed!")
