"""
Simple Tests for Attractions CRUD Operations
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAttractionsCRUDSimple:
    """Simple test suite for Attractions CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_attraction_basic(self, async_client: AsyncClient):
        """Test basic attraction creation with minimal data"""
        # First register a host
        host_data = {
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
        
        # Register host
        register_response = await async_client.post("/api/v1/hosts/register", json=host_data)
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Login to get token
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data["email"],
            "password": host_data["password"]
        })
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Create attraction
        attraction_data = {
            "name": "Test Attraction",
            "description": "A beautiful test attraction in Croatia",
            "attraction_type": "cultural",
            "city": "Zagreb",
            "region": "Zagrebačka",
            "admission_fee": "€10-20",
            "host_personal_tip": "Visit early morning for best experience"
        }
        
        response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == attraction_data["name"]
        assert data["description"] == attraction_data["description"]
        assert data["attraction_type"] == attraction_data["attraction_type"]
        assert data["city"] == attraction_data["city"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_attractions_by_host(self, async_client: AsyncClient):
        """Test retrieving attractions for a host"""
        # Register and login host
        host_data = {
            "email": "test.host2@lovran.com",
            "password": "securepassword123",
            "first_name": "Ana",
            "last_name": "Novak",
            "phone": "+385 51 234 568",
            "business_name": "Villa Ana",
            "business_type": "villa",
            "address": "Oprić 72",
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "local_specialties": ["seafood"],
            "languages": ["hr", "en"],
            "max_group_size": 4,
            "description": "Beautiful villa in Lovran",
            "welcome_message": "Welcome to Villa Ana!"
        }
        
        await async_client.post("/api/v1/hosts/register", json=host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data["email"],
            "password": host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Create an attraction first
        attraction_data = {
            "name": "Lovran Beach",
            "description": "Beautiful pebble beach in Lovran",
            "attraction_type": "natural",
            "city": "Lovran",
            "region": "Primorsko-goranska",
            "admission_fee": "Free"
        }
        
        create_response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        # Get attractions by host
        response = await async_client.get(
            "/api/v1/attractions/host",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check if our attraction is in the list
        attraction_names = [attraction["name"] for attraction in data]
        assert "Lovran Beach" in attraction_names

    @pytest.mark.asyncio
    async def test_update_attraction(self, async_client: AsyncClient):
        """Test updating an attraction"""
        # Register and login host
        host_data = {
            "email": "test.host3@lovran.com",
            "password": "securepassword123",
            "first_name": "Petar",
            "last_name": "Kovač",
            "phone": "+385 51 234 569",
            "business_name": "Apartment Petar",
            "business_type": "apartment",
            "address": "Oprić 73",
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "local_specialties": ["wine_tours"],
            "languages": ["hr", "en"],
            "max_group_size": 3,
            "description": "Cozy apartment",
            "welcome_message": "Welcome!"
        }
        
        await async_client.post("/api/v1/hosts/register", json=host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data["email"],
            "password": host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Create an attraction
        attraction_data = {
            "name": "Original Name",
            "description": "Original description",
            "attraction_type": "cultural",
            "city": "Zagreb",
            "region": "Zagrebačka",
            "admission_fee": "€10"
        }
        
        create_response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        attraction_id = create_response.json()["id"]
        
        # Update the attraction
        update_data = {
            "name": "Updated Name",
            "description": "Updated description with more details",
            "admission_fee": "€15-25",
            "host_personal_tip": "Updated tip: Visit during sunset"
        }
        
        response = await async_client.put(
            f"/api/v1/attractions/{attraction_id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["admission_fee"] == update_data["admission_fee"]
        assert data["host_personal_tip"] == update_data["host_personal_tip"]

    @pytest.mark.asyncio
    async def test_delete_attraction(self, async_client: AsyncClient):
        """Test deleting an attraction"""
        # Register and login host
        host_data = {
            "email": "test.host4@lovran.com",
            "password": "securepassword123",
            "first_name": "Marija",
            "last_name": "Horvat",
            "phone": "+385 51 234 570",
            "business_name": "Villa Marija",
            "business_type": "villa",
            "address": "Oprić 74",
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "local_specialties": ["seafood"],
            "languages": ["hr", "en"],
            "max_group_size": 5,
            "description": "Beautiful villa",
            "welcome_message": "Welcome!"
        }
        
        await async_client.post("/api/v1/hosts/register", json=host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data["email"],
            "password": host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Create an attraction
        attraction_data = {
            "name": "To Be Deleted",
            "description": "This attraction will be deleted",
            "attraction_type": "cultural",
            "city": "Zagreb",
            "region": "Zagrebačka",
            "admission_fee": "€10"
        }
        
        create_response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        attraction_id = create_response.json()["id"]
        
        # Delete the attraction
        response = await async_client.delete(
            f"/api/v1/attractions/{attraction_id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify attraction is deleted
        get_response = await async_client.get(
            f"/api/v1/attractions/{attraction_id}",
            headers=headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test unauthorized access to attraction endpoints"""
        # Test without authentication
        response = await async_client.get("/api/v1/attractions/host")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = await async_client.post("/api/v1/attractions/", json={"name": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.put(f"/api/v1/attractions/{fake_id}", json={"name": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = await async_client.delete(f"/api/v1/attractions/{fake_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_attraction_validation_errors(self, async_client: AsyncClient):
        """Test attraction creation with validation errors"""
        # Register and login host
        host_data = {
            "email": "test.host5@lovran.com",
            "password": "securepassword123",
            "first_name": "Ivan",
            "last_name": "Milić",
            "phone": "+385 51 234 571",
            "business_name": "Apartment Ivan",
            "business_type": "apartment",
            "address": "Oprić 75",
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2742,
            "local_specialties": ["seafood"],
            "languages": ["hr", "en"],
            "max_group_size": 4,
            "description": "Cozy apartment",
            "welcome_message": "Welcome!"
        }
        
        await async_client.post("/api/v1/hosts/register", json=host_data)
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data["email"],
            "password": host_data["password"]
        })
        token = login_response.json()["session_token"]
        headers = {"X-Session-Token": token}
        
        # Test missing required fields
        invalid_data = {
            "description": "Missing name and category"
        }
        
        response = await async_client.post(
            "/api/v1/attractions/",
            json=invalid_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
