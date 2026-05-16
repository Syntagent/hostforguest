"""
Tests for host API endpoints.

Tests host registration, authentication, and CRUD operations through
the REST API for the Croatian tourist host platform.
"""

import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

from app.models.host import HostCreate, HostLogin


class TestHostEndpoints:
    """Test suite for host API endpoints."""
    
    @pytest.fixture
    def sample_host_data(self):
        """Sample host registration data."""
        return {
            "email": "test.host@lovran.com",
            "password": "securepassword123",
            "first_name": "Marko",
            "last_name": "Petrić",
            "phone": "+385 51 234 567",
            "business_name": "Apartment Lovran",
            "business_type": "apartment",
            "address": "Oprić 71",
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "local_specialties": ["seafood", "wine_tours"],
            "languages": ["hr", "en"],
            "max_group_size": 6,
            "description": "Cozy apartment in the heart of Lovran",
            "welcome_message": "Welcome to our beautiful Lovran apartment!"
        }
    
    @pytest.fixture
    def sample_profile_data(self):
        """Sample host profile data."""
        return {
            "property_type": "apartment",
            "number_of_rooms": 2,
            "max_guests": 4,
            "services_offered": ["wifi", "parking"],
            "amenities": ["kitchen", "balcony", "air_conditioning"],
            "expertise_areas": ["local_restaurants", "beaches"],
            "favorite_local_spots": [
                {
                    "name": "Lovran Beach",
                    "type": "beach",
                    "description": "Beautiful pebble beach"
                }
            ]
        }
    
    async def test_register_host_success(self, async_client: AsyncClient, sample_host_data: dict):
        """Test successful host registration."""
        # Act
        response = await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == sample_host_data["email"]
        assert data["first_name"] == sample_host_data["first_name"]
        assert data["city"] == "Lovran"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned
    
    async def test_register_host_duplicate_email(self, async_client: AsyncClient, sample_host_data: dict):
        """Test registration with duplicate email fails."""
        # Arrange - register first host
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        
        # Act - try to register with same email
        response = await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    async def test_register_host_invalid_data(self, async_client: AsyncClient):
        """Test registration with invalid data."""
        invalid_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "123",  # Too short password
            "first_name": "",  # Empty required field
            "address": "Test Address",
            "city": "Lovran"
        }
        
        # Act
        response = await async_client.post("/api/v1/hosts/register", json=invalid_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_host_email_normalized_lowercase(self, async_client: AsyncClient, sample_host_data: dict):
        """Registered host email is stored lowercase (HostCreate validator + service)."""
        unique = uuid.uuid4().hex[:10]
        payload = {**sample_host_data, "email": f"MiXeD-{unique}@Sub.Example.COM"}
        r = await async_client.post("/api/v1/hosts/register", json=payload)
        assert r.status_code == status.HTTP_201_CREATED, r.text
        assert r.json()["email"] == f"mixed-{unique}@sub.example.com"

    async def test_register_duplicate_email_case_insensitive(self, async_client: AsyncClient, sample_host_data: dict):
        """Second registration with same email different casing is rejected."""
        token = uuid.uuid4().hex[:12]
        first = {**sample_host_data, "email": f"CaseDup-{token}@Example.COM"}
        r1 = await async_client.post("/api/v1/hosts/register", json=first)
        assert r1.status_code == status.HTTP_201_CREATED, r1.text
        second = {**sample_host_data, "email": f"casedup-{token}@example.com", "business_name": "Other Biz"}
        r2 = await async_client.post("/api/v1/hosts/register", json=second)
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in r2.json()["detail"]

    async def test_login_invalid_email_format_422(self, async_client: AsyncClient):
        """Login body must satisfy HostLogin email validation."""
        r = await async_client.post(
            "/api/v1/hosts/login",
            json={"email": "not-an-email", "password": "whatever12345"},
        )
        assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_login_host_success(self, async_client: AsyncClient, sample_host_data: dict):
        """Test successful host login."""
        # Arrange - register host first
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        
        login_data = {
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        }
        
        # Act
        response = await async_client.post("/api/v1/hosts/login", json=login_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("success") is True
        assert "session_token" in data
        assert "refresh_token" in data
        assert "host" in data
        assert data["host"]["email"] == sample_host_data["email"]
    
    async def test_login_host_invalid_credentials(self, async_client: AsyncClient, sample_host_data: dict):
        """Test login with invalid credentials."""
        # Arrange - register host first
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        
        login_data = {
            "email": sample_host_data["email"],
            "password": "wrongpassword"
        }
        
        # Act
        response = await async_client.post("/api/v1/hosts/login", json=login_data)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]
    
    async def test_login_nonexistent_host(self, async_client: AsyncClient):
        """Test login with non-existent email."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "anypassword"
        }
        
        # Act
        response = await async_client.post("/api/v1/hosts/login", json=login_data)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_get_current_host_profile(self, async_client: AsyncClient, sample_host_data: dict):
        """Test getting current host profile."""
        # Arrange - register and login
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Act
        response = await async_client.get("/api/v1/hosts/me", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == sample_host_data["email"]
        assert data["first_name"] == sample_host_data["first_name"]
        assert data["city"] == "Lovran"
    
    async def test_get_current_host_unauthorized(self, async_client: AsyncClient):
        """Test getting current host without authentication."""
        # Act
        response = await async_client.get("/api/v1/hosts/me")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_update_current_host(self, async_client: AsyncClient, sample_host_data: dict):
        """Test updating current host profile."""
        # Arrange - register and login
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        update_data = {
            "first_name": "Updated Marko",
            "description": "Updated description for apartment",
            "max_group_size": 8
        }
        
        # Act
        response = await async_client.put("/api/v1/hosts/me", json=update_data, headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == "Updated Marko"
        assert data["description"] == "Updated description for apartment"
        assert data["max_group_size"] == 8
        assert data["last_name"] == sample_host_data["last_name"]  # Unchanged
    
    async def test_delete_current_host(self, async_client: AsyncClient, sample_host_data: dict):
        """Test deleting current host account."""
        # Arrange - register and login
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Act
        response = await async_client.delete("/api/v1/hosts/me", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify host can no longer login
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_get_host_by_id(self, async_client: AsyncClient, sample_host_data: dict):
        """Test getting host by ID (public endpoint)."""
        # Arrange - register host
        register_response = await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        host_id = register_response.json()["id"]
        
        # Act
        response = await async_client.get(f"/api/v1/hosts/{host_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == host_id
        assert data["email"] == sample_host_data["email"]
        assert data["city"] == "Lovran"
    
    async def test_get_host_by_invalid_id(self, async_client: AsyncClient):
        """Test getting host with invalid ID."""
        # Act
        response = await async_client.get(f"/api/v1/hosts/{uuid.uuid4()}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_list_hosts(self, async_client: AsyncClient, sample_host_data: dict):
        """Test listing hosts."""
        # Arrange - create multiple hosts
        for i in range(3):
            host_data = sample_host_data.copy()
            host_data["email"] = f"host{i}@example.com"
            host_data["first_name"] = f"Host{i}"
            await async_client.post("/api/v1/hosts/register", json=host_data)
        
        # Act
        response = await async_client.get("/api/v1/hosts/")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(host["is_active"] for host in data)
    
    async def test_list_hosts_with_pagination(self, async_client: AsyncClient, sample_host_data: dict):
        """Test listing hosts with pagination."""
        # Arrange - create multiple hosts
        for i in range(5):
            host_data = sample_host_data.copy()
            host_data["email"] = f"host{i}@example.com"
            await async_client.post("/api/v1/hosts/register", json=host_data)
        
        # Act
        response = await async_client.get("/api/v1/hosts/?skip=1&limit=2")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
    
    async def test_search_hosts_by_city(self, async_client: AsyncClient, sample_host_data: dict):
        """Test searching hosts by city."""
        # Arrange - create hosts in different cities
        lovran_host = sample_host_data.copy()
        lovran_host["email"] = "lovran@example.com"
        lovran_host["city"] = "Lovran"
        await async_client.post("/api/v1/hosts/register", json=lovran_host)
        
        opatija_host = sample_host_data.copy()
        opatija_host["email"] = "opatija@example.com"
        opatija_host["city"] = "Opatija"
        await async_client.post("/api/v1/hosts/register", json=opatija_host)
        
        # Act
        response = await async_client.get("/api/v1/hosts/?city=Lovran")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["city"] == "Lovran"
    
    async def test_create_host_profile(self, async_client: AsyncClient, sample_host_data: dict, sample_profile_data: dict):
        """Test creating host profile."""
        # Arrange - register and login
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Act
        response = await async_client.post("/api/v1/hosts/me/profile", json=sample_profile_data, headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["property_type"] == "apartment"
        assert data["number_of_rooms"] == 2
        assert "wifi" in data["services_offered"]
        assert "kitchen" in data["amenities"]
    
    async def test_create_duplicate_host_profile(self, async_client: AsyncClient, sample_host_data: dict, sample_profile_data: dict):
        """Test creating duplicate host profile fails."""
        # Arrange - register, login, and create profile
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Create first profile
        await async_client.post("/api/v1/hosts/me/profile", json=sample_profile_data, headers=headers)
        
        # Act - try to create another profile
        response = await async_client.post("/api/v1/hosts/me/profile", json=sample_profile_data, headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_get_host_profile(self, async_client: AsyncClient, sample_host_data: dict, sample_profile_data: dict):
        """Test getting host profile."""
        # Arrange - register, login, and create profile
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        await async_client.post("/api/v1/hosts/me/profile", json=sample_profile_data, headers=headers)
        
        # Act
        response = await async_client.get("/api/v1/hosts/me/profile", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["property_type"] == "apartment"
        assert data["number_of_rooms"] == 2
    
    async def test_get_nonexistent_host_profile(self, async_client: AsyncClient, sample_host_data: dict):
        """Test getting non-existent host profile."""
        # Arrange - register and login (but don't create profile)
        await async_client.post("/api/v1/hosts/register", json=sample_host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": sample_host_data["email"],
            "password": sample_host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Act
        response = await async_client.get("/api/v1/hosts/me/profile", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_invalid_token(self, async_client: AsyncClient):
        """Test API calls with invalid token."""
        headers = {"X-Session-Token": "invalid-session-token-not-issued"}
        
        # Act
        response = await async_client.get("/api/v1/hosts/me", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED 