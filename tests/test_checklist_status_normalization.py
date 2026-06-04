"""AI checklist_updates must use API statuses (draft not drafted)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_ingest_accepts_drafted_status_from_agent(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services.host_onboarding_service import HostOnboardingService

    async def fake_turn(self, **kwargs):
        return {
            "success": True,
            "reply": "Updated property story draft.",
            "quick_replies": ["Apply draft"],
            "suggested_patch": {"location_story": "Nature, sea, and Mount Učka."},
            "suggestion_options": [],
            "actions": [],
            "checklist_updates": [{"id": "location_story", "status": "drafted"}],
            "next_focus_id": "amenities",
            "metadata": {"provider": "test"},
        }

    monkeypatch.setattr(HostOnboardingService, "accommodation_agent_turn", fake_turn)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/voice/ingest",
        headers=host_token_headers,
        json={
            "message": "emphasize nature, sea and Učka in property story",
            "focused_item_id": "location_story",
            "checklist_state": [{"id": "location_story", "status": "in_progress"}],
            "accommodation_snapshot": {"location_story": "Lovran stay."},
            "conversation_history": [],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checklist_updates"][0]["status"] == "draft"
    assert body["metadata"]["ingested_via"] == "voice"
    assert body["suggested_patch"]["location_story"]
