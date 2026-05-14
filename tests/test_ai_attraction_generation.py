"""
Test AI-powered attraction content generation functionality.

Uses HTTP register/login so the session lives in the same DB as the ASGI app (get_db).
"""

import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest


async def _register_and_login(client: httpx.AsyncClient, suffix: str) -> str:
    email = f"ai_attr_{suffix}@example.com"
    reg = await client.post(
        "/api/v1/hosts/register",
        json={
            "email": email,
            "password": "testpassword123",
            "first_name": "A",
            "last_name": "B",
            "address": "1 St",
            "city": "Lovran",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert login.status_code == 200, login.text
    return login.json()["session_token"]


class TestAIAttractionGeneration:
    """Test AI attraction content generation."""

    @pytest.mark.asyncio
    async def test_generate_attraction_content_success(self, async_client: httpx.AsyncClient):
        """Test successful AI content generation for attraction."""
        token = await _register_and_login(async_client, uuid.uuid4().hex[:12])

        with patch("app.api.v1.attractions.HostOnboardingService") as mock_onboarding_service:
            mock_service_instance = MagicMock()
            mock_onboarding_service.return_value = mock_service_instance

            mock_result = {
                "success": True,
                "attractions": [
                    {
                        "name": "Test Attraction",
                        "description": "A wonderful test attraction in Croatia",
                        "category": "Restaurant",
                        "location": "Lovran",
                        "cost_estimate": "€10-20",
                        "authenticity_level": "high",
                        "host_tips": ["Visit during lunch hours"],
                        "best_time": "lunch",
                        "accessibility": "moderate",
                        "crowd_level": "moderate",
                        "local_insights": "Local favorite spot",
                    }
                ],
                "data_source": "archon",
                "sources_used": 3,
                "personalization_level": "expert",
            }

            async def mock_generate_suggestions(*args, **kwargs):
                return mock_result

            mock_service_instance.generate_local_attraction_suggestions = mock_generate_suggestions

            response = await async_client.post(
                "/api/v1/attractions/generate-content",
                json={
                    "name": "Test Attraction",
                    "category": "Restaurant",
                    "location": "Lovran",
                    "host_interests": ["food", "culture"],
                },
                headers={"X-Session-Token": token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "content" in data
            assert data["content"]["name"] == "Test Attraction"
            assert data["content"]["description"] == "A wonderful test attraction in Croatia"
            assert data["content"]["category"] == "Restaurant"
            assert data["content"]["location"] == "Lovran"
            assert data["content"]["cost_estimate"] == "€10-20"
            assert data["content"]["authenticity_level"] == "high"
            assert data["content"]["enhanced"] is True
            assert data["content"]["ai_generated"] is True
            assert data["data_source"] == "archon"
            assert data["sources_used"] == 3
            assert data["personalization_level"] == "expert"

    @pytest.mark.asyncio
    async def test_generate_attraction_content_missing_name(self, async_client: httpx.AsyncClient):
        """Test AI content generation with missing attraction name."""
        token = await _register_and_login(async_client, uuid.uuid4().hex[:12])

        response = await async_client.post(
            "/api/v1/attractions/generate-content",
            json={
                "category": "Restaurant",
                "location": "Lovran",
            },
            headers={"X-Session-Token": token},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Attraction name is required" in data["detail"]

    @pytest.mark.asyncio
    async def test_generate_attraction_content_unauthorized(self, async_client: httpx.AsyncClient):
        """Test AI content generation without authentication."""
        response = await async_client.post(
            "/api/v1/attractions/generate-content",
            json={
                "name": "Test Attraction",
                "category": "Restaurant",
                "location": "Lovran",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_attraction_content_with_host_interests(self, async_client: httpx.AsyncClient):
        """Test AI content generation with host interests for personalization."""
        token = await _register_and_login(async_client, uuid.uuid4().hex[:12])

        with patch("app.api.v1.attractions.HostOnboardingService") as mock_onboarding_service:
            mock_service_instance = MagicMock()
            mock_onboarding_service.return_value = mock_service_instance

            mock_result = {
                "success": True,
                "attractions": [
                    {
                        "name": "Cultural Museum",
                        "description": "A fascinating museum showcasing local history",
                        "category": "Museum",
                        "location": "Lovran",
                        "cost_estimate": "€5-10",
                        "authenticity_level": "very_high",
                        "host_tips": ["Visit on weekdays for fewer crowds", "Guided tours available"],
                        "best_time": "morning",
                        "accessibility": "high",
                        "crowd_level": "low",
                        "local_insights": "Perfect for culture enthusiasts",
                    }
                ],
                "data_source": "archon",
                "sources_used": 5,
                "personalization_level": "expert",
            }

            async def mock_generate_suggestions(*args, **kwargs):
                return mock_result

            mock_service_instance.generate_local_attraction_suggestions = mock_generate_suggestions

            response = await async_client.post(
                "/api/v1/attractions/generate-content",
                json={
                    "name": "Cultural Museum",
                    "category": "Museum",
                    "location": "Lovran",
                    "host_interests": ["history", "culture", "museums"],
                },
                headers={"X-Session-Token": token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["content"]["name"] == "Cultural Museum"
            assert data["content"]["category"] == "Museum"
            assert data["content"]["authenticity_level"] == "very_high"
            assert len(data["content"]["host_tips"]) >= 1
            assert data["personalization_level"] == "expert"
