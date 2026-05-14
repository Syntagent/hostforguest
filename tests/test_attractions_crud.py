"""
Tests for Attractions CRUD Operations (session auth + current API schema).
"""
import pytest
from httpx import AsyncClient

from app.models.attraction import Attraction
from app.models.host import Host


async def host_session_headers(async_client: AsyncClient, test_host: Host) -> dict[str, str]:
    """Hosts authenticate with X-Session-Token (see app/api/v1/attractions.py)."""
    login_response = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": test_host.email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["session_token"]
    return {"X-Session-Token": token}


class TestAttractionsCRUD:
    """Test suite for Attractions CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_attraction_success(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        attraction_data = {
            "name": "Test Attraction",
            "description": "A beautiful test attraction in Croatia",
            "attraction_type": "cultural",
            "city": "Zagreb",
            "admission_fee": "€10-20",
            "host_personal_tip": "Visit early morning for best experience",
        }

        response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == attraction_data["name"]
        assert data["description"] == attraction_data["description"]
        assert data["attraction_type"] == attraction_data["attraction_type"]
        assert data["city"] == attraction_data["city"]
        assert data["created_by_host_id"] == str(test_host.id)
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_attraction_with_google_places_data(
        self, async_client: AsyncClient, test_host: Host
    ):
        """Create flow uses AttractionCreate only; extra vendor fields are not stored on the model."""
        headers = await host_session_headers(async_client, test_host)
        attraction_data = {
            "name": "Konoba Stari Grad",
            "description": "Traditional Croatian restaurant",
            "attraction_type": "culinary",
            "city": "Lovran",
            "admission_fee": "€20-40",
        }

        response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == attraction_data["name"]
        assert data["city"] == "Lovran"

    @pytest.mark.asyncio
    async def test_get_attractions_by_host(
        self,
        async_client: AsyncClient,
        test_host: Host,
        test_attraction: Attraction,
    ):
        headers = await host_session_headers(async_client, test_host)

        response = await async_client.get(
            "/api/v1/attractions/host",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        attraction_ids = [a["id"] for a in data]
        assert str(test_attraction.id) in attraction_ids

    @pytest.mark.asyncio
    async def test_get_attraction_by_id(
        self, async_client: AsyncClient, test_attraction: Attraction
    ):
        """Public read by id — no session required."""
        response = await async_client.get(
            f"/api/v1/attractions/{test_attraction.id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_attraction.id)
        assert data["name"] == test_attraction.name
        assert data["description"] == test_attraction.description

    @pytest.mark.asyncio
    async def test_update_attraction_success(
        self,
        async_client: AsyncClient,
        test_host: Host,
        test_attraction: Attraction,
    ):
        headers = await host_session_headers(async_client, test_host)
        update_data = {
            "name": "Updated Test Attraction",
            "description": "Updated description with more details",
            "admission_fee": "€15-25",
            "host_personal_tip": "Updated tip: visit during sunset",
        }

        response = await async_client.put(
            f"/api/v1/attractions/{test_attraction.id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["admission_fee"] == update_data["admission_fee"]
        assert data["host_personal_tip"] == update_data["host_personal_tip"]

    @pytest.mark.asyncio
    async def test_delete_attraction_success(
        self,
        async_client: AsyncClient,
        test_host: Host,
        test_attraction: Attraction,
    ):
        headers = await host_session_headers(async_client, test_host)

        response = await async_client.delete(
            f"/api/v1/attractions/{test_attraction.id}",
            headers=headers,
        )

        assert response.status_code == 204

        get_response = await async_client.get(
            f"/api/v1/attractions/{test_attraction.id}",
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_attraction_analytics(
        self,
        async_client: AsyncClient,
        test_host: Host,
        test_attraction: Attraction,
    ):
        headers = await host_session_headers(async_client, test_host)

        response = await async_client.get(
            f"/api/v1/attractions/{test_attraction.id}/analytics",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "recommendations" in data
        assert "average_rating" in data
        assert "review_count" in data
        assert "guest_feedback" in data
        assert isinstance(data["views"], int)
        assert isinstance(data["recommendations"], int)
        assert isinstance(data["average_rating"], (int, float))
        assert isinstance(data["review_count"], int)
        assert isinstance(data["guest_feedback"], list)

    @pytest.mark.asyncio
    async def test_create_attraction_validation_errors(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        invalid_data = {"description": "Missing name and attraction_type"}

        response = await async_client.post(
            "/api/v1/attractions/",
            json=invalid_data,
            headers=headers,
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_update_attraction_not_found(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.put(
            f"/api/v1/attractions/{fake_id}",
            json={"name": "Updated Name"},
            headers=headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_attraction_not_found(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.delete(
            f"/api/v1/attractions/{fake_id}",
            headers=headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self, async_client: AsyncClient, test_attraction: Attraction
    ):
        """GET by id is public; mutating routes require X-Session-Token."""
        response = await async_client.get(
            f"/api/v1/attractions/{test_attraction.id}",
        )
        assert response.status_code == 200

        response = await async_client.put(
            f"/api/v1/attractions/{test_attraction.id}",
            json={"name": "Test"},
        )
        assert response.status_code == 401

        response = await async_client.delete(
            f"/api/v1/attractions/{test_attraction.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_attraction_search_and_filtering(
        self, async_client: AsyncClient, test_host: Host
    ):
        """Public list supports city / attraction_type / category query params."""
        _ = await host_session_headers(async_client, test_host)

        response = await async_client.get(
            "/api/v1/attractions/?attraction_type=cultural",
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        response = await async_client.get("/api/v1/attractions/?city=Zagreb")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_attraction_with_coordinates(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        attraction_data = {
            "name": "Geolocated Attraction",
            "description": "An attraction with precise coordinates",
            "attraction_type": "historic",
            "city": "Split",
            "latitude": 43.5081,
            "longitude": 16.4402,
            "admission_fee": "Free",
        }

        response = await async_client.post(
            "/api/v1/attractions/",
            json=attraction_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["latitude"] == attraction_data["latitude"]
        assert data["longitude"] == attraction_data["longitude"]


class TestAttractionContentGeneration:
    """AI content generation (requires host session)."""

    @pytest.mark.asyncio
    async def test_generate_attraction_content(
        self, async_client: AsyncClient, test_host: Host
    ):
        headers = await host_session_headers(async_client, test_host)
        generation_data = {
            "name": "Plitvice Lakes",
            "category": "nature",
            "location": "Plitvice Lakes National Park, Croatia",
            "host_interests": ["nature", "photography", "hiking"],
        }

        response = await async_client.post(
            "/api/v1/attractions/generate-content",
            json=generation_data,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data
        assert "data_source" in data
        assert "sources_used" in data
        assert "personalization_level" in data
        content = data["content"]
        assert isinstance(content, dict)
