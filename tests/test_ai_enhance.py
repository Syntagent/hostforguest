"""
Tests for the AI enhancement endpoint: /api/v1/attractions/ai-enhance
"""

import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch


@pytest.mark.asyncio
async def test_ai_enhance_success(async_client: httpx.AsyncClient, async_db_session: AsyncSession):
    """Returns AI-generated description when AIService succeeds."""
    from tests.conftest import create_test_host_async
    from app.services.session_service import SessionService

    host = await create_test_host_async(async_db_session, "host@example.com")
    session_service = SessionService(async_db_session)
    session_data = await session_service.create_session(host.id)

    payload = {
        "attraction_name": "Art-kino Croatia",
        "location": "Krešimirova ul. 2, Rijeka, Croatia",
        "attraction_type": "movie_theater",
        "current_description": "",
        "host_location": "Lovran, Croatia",
        "distance_from_host": "~15 km",
        "nearby_places": [
            {"name": "Korzo", "types": ["point_of_interest"]},
            {"name": "Trsat Castle", "types": ["tourist_attraction"]},
        ],
        "google_places_data": {"rating": 4.6, "user_ratings_total": 1200, "price_level": 2, "types": ["movie_theater", "point_of_interest"]},
    }

    with patch("app.services.ai_service.AIService") as mock_ai_service:
        instance = mock_ai_service.return_value
        async def _mock_generate_chat_response(*args, **kwargs):
            return {"success": True, "response": "Art-kino Croatia is a cinema in Rijeka offering curated films."}
        instance.generate_chat_response = _mock_generate_chat_response

        resp = await async_client.post(
            "/api/v1/attractions/ai-enhance",
            json=payload,
            headers={"X-Session-Token": session_data["session_token"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "enhanced_description" in data["data"]
    assert len(data["data"]["enhanced_description"]) > 10
    assert data["data"]["enhancement_method"] == "ai_generated"


@pytest.mark.asyncio
async def test_ai_enhance_fallback(async_client: httpx.AsyncClient, async_db_session: AsyncSession):
    """Falls back to generated copy when AIService fails."""
    from tests.conftest import create_test_host_async
    from app.services.session_service import SessionService

    host = await create_test_host_async(async_db_session, "host2@example.com")
    session_service = SessionService(async_db_session)
    session_data = await session_service.create_session(host.id)

    payload = {
        "attraction_name": "Art-kino Croatia",
        "location": "Rijeka, Croatia",
        "attraction_type": "movie_theater",
        "current_description": "",
        "host_location": "Lovran, Croatia",
        "distance_from_host": "~15 km",
        "nearby_places": [],  # ensure no placeholder commas appear
        "google_places_data": {"rating": 4.6, "user_ratings_total": 1200, "price_level": 2, "types": ["movie_theater"]},
    }

    with patch("app.services.ai_service.AIService") as mock_ai_service:
        instance = mock_ai_service.return_value
        async def _mock_generate_chat_response(*args, **kwargs):
            return {"success": False, "response": ""}
        instance.generate_chat_response = _mock_generate_chat_response

        resp = await async_client.post(
            "/api/v1/attractions/ai-enhance",
            json=payload,
            headers={"X-Session-Token": session_data["session_token"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    text = data["data"]["enhanced_description"]
    assert "Art-kino Croatia" in text
    assert ", ," not in text  # no empty nearby list artifacts
    assert data["data"]["enhancement_method"] == "fallback_generated"


