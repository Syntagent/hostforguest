"""Focused tests for the Stay-tab accommodation AI onboarding agent."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.services.ai_service_fallback import AIServiceWithFallback


@pytest.mark.asyncio
async def test_accommodation_agent_requires_auth(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/onboarding/accommodation/agent/message",
        json={
            "message": "We have sea view and homemade olive oil.",
            "focused_item_id": "location_story",
            "checklist_state": [],
            "accommodation_snapshot": {},
            "conversation_history": [],
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_accommodation_agent_returns_patch_safe_response(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_structured_response(self, **kwargs):
        return {
            "success": True,
            "provider": "test",
            "model": "mock",
            "structured_data": {
                "reply": "That sea-view detail is strong. Here is a guest-ready draft.",
                "quick_replies": ["Apply draft", "Make it warmer"],
                "suggested_patch": {
                    "location_story": "Wake up near the Kvarner sea with homemade olive oil and local host tips.",
                    "amenities": ["should_not_be_allowed_for_story"],
                },
                "checklist_updates": [{"id": "location_story", "status": "draft"}],
                "next_focus_id": "amenities",
            },
        }

    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", fake_structured_response)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/agent/message",
        headers=host_token_headers,
        json={
            "message": "We have sea view and homemade olive oil.",
            "focused_item_id": "location_story",
            "checklist_state": [{"id": "location_story", "status": "missing"}],
            "accommodation_snapshot": {"city": "Lovran", "property_type": "apartment"},
            "conversation_history": [],
        },
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    assert body["suggested_patch"]["location_story"].startswith("Wake up")
    assert body["suggested_patch"]["amenities"] is None
    assert body["checklist_updates"][0]["status"] == "draft"
    assert body["next_focus_id"] == "amenities"


@pytest.mark.asyncio
async def test_accommodation_agent_falls_back_when_ai_fails(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    async def failing_structured_response(self, **kwargs):
        return {"success": False, "error": "no model"}

    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", failing_structured_response)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/agent/message",
        headers=host_token_headers,
        json={
            "message": "Breakfast baskets on request, bike storage, and quiet garden.",
            "focused_item_id": "services",
            "checklist_state": [{"id": "services", "status": "missing"}],
            "accommodation_snapshot": {"city": "Lovran"},
            "conversation_history": [],
        },
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    assert body["metadata"]["provider"] == "fallback"
    assert body["suggested_patch"]["services_offered"]

