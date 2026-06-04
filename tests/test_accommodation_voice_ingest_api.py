"""Voice /ingest must run the same accommodation agent as typed messages."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_ingest_with_transcript_returns_location_story_patch(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
):
    response = await async_client.post(
        "/api/v1/onboarding/accommodation/voice/ingest",
        headers=host_token_headers,
        json={
            "message": "in property story emphasize nature, closeness to sea and Učka mountain",
            "focused_item_id": "location_story",
            "checklist_state": [{"id": "location_story", "status": "in_progress"}],
            "accommodation_snapshot": {
                "city": "Lovran",
                "property_type": "apartment",
                "location_story": (
                    "Our property is embraced by the stunning natural landscapes of Lovran."
                ),
            },
            "conversation_history": [],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("reply")
    patch = body.get("suggested_patch") or {}
    assert patch.get("location_story")
    assert body.get("metadata", {}).get("ingested_via") == "voice"
