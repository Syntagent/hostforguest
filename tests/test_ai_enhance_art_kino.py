"""
Focused tests for /api/v1/attractions/ai-enhance using Art-kino context.
Includes:
- Mocked provider test (fast, always runs)
- Live provider test (opt-in via TEST_REAL_AI=1 and USE_WEB_SEARCH=1)
"""

import os
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch


@pytest.mark.asyncio
async def test_ai_enhance_art_kino_mock(async_client: httpx.AsyncClient, async_db_session: AsyncSession):
    from tests.conftest import create_test_host_async
    from app.services.session_service import SessionService

    host = await create_test_host_async(async_db_session, "artkino-mock@example.com")
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
        "google_places_data": {
            "rating": 4.6,
            "user_ratings_total": 1200,
            "price_level": 2,
            "types": ["movie_theater", "point_of_interest"],
        },
        "use_web_search": True,
    }

    with patch("app.services.ai_service.AIService.generate_chat_response") as mock_gen:
        async def _mock_gen(*args, **kwargs):
            # ensure flag propagated
            assert kwargs.get("use_web_search") is True
            return {"success": True, "response": "Curated film program with local and international titles; cozy single-screen venue."}

        mock_gen.side_effect = _mock_gen

        resp = await async_client.post(
            "/api/v1/attractions/ai-enhance",
            json=payload,
            headers={"X-Session-Token": session_data["session_token"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    text = data["data"]["enhanced_description"]
    assert "Art-kino Croatia is a movie theater" in text
    assert "Good to know:" in text
    assert "Rated" in text or "Typical cost" in text or "Distance" in text


pytestmark_live = pytest.mark.skipif(
    os.getenv("TEST_REAL_AI") != "1", reason="Set TEST_REAL_AI=1 to run live Art-kino test",
)


@pytestmark_live
@pytest.mark.asyncio
async def test_ai_enhance_art_kino_live(async_client: httpx.AsyncClient, async_db_session: AsyncSession, capsys):
    from tests.conftest import create_test_host_async
    from app.services.session_service import SessionService

    host = await create_test_host_async(async_db_session, "artkino-live@example.com")
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
        "google_places_data": {
            "rating": 4.6,
            "user_ratings_total": 1200,
            "price_level": 2,
            "types": ["movie_theater", "point_of_interest"],
        },
        "use_web_search": True,
    }

    resp = await async_client.post(
        "/api/v1/attractions/ai-enhance",
        json=payload,
        headers={"X-Session-Token": session_data["session_token"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    text = data["data"]["enhanced_description"].strip()
    print("\n=== Art-kino (LIVE) ===\n" + text + "\n=======================\n")
    # basic assertions for structure richness
    assert "Art-kino Croatia is a" in text
    assert "Good to know:" in text
    assert len(text) > 80

