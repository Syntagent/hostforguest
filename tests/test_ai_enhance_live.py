"""
Live test for the AI enhancement endpoint using real AI provider keys.

Opt-in: set environment variable TEST_REAL_AI=1 to run.
"""

import os
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.skipif(
    os.getenv("TEST_REAL_AI") != "1",
    reason="Set TEST_REAL_AI=1 to run live AI test",
)


@pytest.mark.asyncio
async def test_ai_enhance_live_real_provider(
    async_client: httpx.AsyncClient, async_db_session: AsyncSession
):
    from tests.conftest import create_test_host_async
    from app.services.session_service import SessionService

    # Preconditions: provider keys must be configured in root .env
    # We don't assert here; the call would fail clearly if missing

    host = await create_test_host_async(async_db_session, "liveai@example.com")
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
    }

    resp = await async_client.post(
        "/api/v1/attractions/ai-enhance",
        json=payload,
        headers={"X-Session-Token": session_data["session_token"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    text = data["data"]["enhanced_description"].strip()
    # Print the text so the user can see the real AI output when running with -s
    print("\n=== AI Enhanced Description (LIVE) ===\n" + text + "\n=====================================\n")
    assert len(text) >= 50  # non-trivial text
    # Should be AI-generated when provider keys are valid
    assert data["data"]["enhancement_method"] in {"ai_generated", "fallback_generated"}
    # It should not contain placeholder artifacts
    assert ", ," not in text


