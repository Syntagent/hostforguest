"""Focused tests for the Stay-tab accommodation AI onboarding agent."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.services.ai_service_fallback import AIServiceWithFallback
from app.services.host_onboarding_service import HostOnboardingService


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
                "actions": [
                    {
                        "action": "update_draft",
                        "target_item_id": "location_story",
                        "patch": {
                            "location_story": "Wake up near the Kvarner sea with homemade olive oil and local host tips.",
                            "amenities": ["should_not_be_allowed_for_story"],
                        },
                    }
                ],
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
    assert body["actions"][0]["action"] == "update_draft"
    assert body["actions"][0]["patch"]["location_story"].startswith("Wake up")
    assert body["actions"][0]["patch"]["amenities"] is None
    assert body["checklist_updates"][0]["status"] == "draft"
    assert body["next_focus_id"] == "amenities"


@pytest.mark.asyncio
async def test_accommodation_agent_receives_guided_option_context(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured_prompt = ""

    async def fake_structured_response(self, **kwargs):
        nonlocal captured_prompt
        captured_prompt = kwargs["messages"][1]["content"]
        return {
            "success": True,
            "provider": "test",
            "model": "mock",
            "structured_data": {
                "reply": "Good correction. I removed pool and kept the remaining amenities.",
                "quick_replies": [],
                "suggested_patch": {
                    "amenities": ["wifi", "air_conditioning", "parking"],
                },
                "actions": [
                    {
                        "action": "replace_draft",
                        "target_item_id": "amenities",
                        "patch": {"amenities": ["wifi", "air_conditioning", "parking"]},
                    }
                ],
                "checklist_updates": [{"id": "amenities", "status": "draft"}],
                "next_focus_id": "services",
            },
        }

    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", fake_structured_response)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/agent/message",
        headers=host_token_headers,
        json={
            "message": "actually no pool",
            "focused_item_id": "amenities",
            "checklist_state": [{"id": "amenities", "status": "in_progress"}],
            "accommodation_snapshot": {
                "city": "Lovran",
                "_agent_context": {
                    "option_field": "amenities",
                    "visible_options": ["wifi", "air_conditioning", "parking", "pool"],
                    "pending_patch": {"amenities": ["wifi", "air_conditioning", "parking", "pool"]},
                },
            },
            "conversation_history": [
                {"role": "assistant", "content": "Do you have any of these amenities?"},
                {"role": "user", "content": "all of them"},
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["suggested_patch"]["amenities"] == ["wifi", "air_conditioning", "parking"]
    assert body["actions"][0]["action"] == "replace_draft"
    assert "visible_options" in captured_prompt
    assert "pending_patch" in captured_prompt
    assert "Available domain actions" in captured_prompt
    assert "actually no pool" in captured_prompt
    assert "Never put meta-phrases" in captured_prompt


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


@pytest.mark.asyncio
async def test_accommodation_ai_enhance_handles_dict_profile_and_fallback(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_host_profile(self, host_id):
        return {
            "city": "Lovran",
            "local_knowledge_level": "expert",
            "host_interests": ["Gastronomy", "Nature"],
        }

    async def failing_structured_response(self, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(HostOnboardingService, "get_host_profile", fake_host_profile)
    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", failing_structured_response)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/ai-enhance",
        headers=host_token_headers,
        json={
            "current_data": {
                "property_name": "Ben Host Stay Lovran",
                "property_type": "apartment",
                "location_story": "",
                "max_guests": 12,
                "number_of_rooms": 3,
                "amenities": [],
                "services_offered": [],
                "expertise_areas": ["Gastronomy"],
                "city": "Lovran",
                "county": "Kvarner",
            },
            "enhancement_type": "comprehensive",
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    assert body["enhanced_content"]["description"]
    assert body["enhanced_content"]["amenities"]
    assert body["metadata"]["ai_provider"] == "fallback"


@pytest.mark.asyncio
async def test_accommodation_ai_enhance_normalizes_alternate_ai_fields(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_host_profile(self, host_id):
        return {"city": "Lovran", "local_knowledge_level": "expert", "host_interests": []}

    async def alternate_structured_response(self, **kwargs):
        return {
            "success": True,
            "provider": "test",
            "structured_data": {
                "business_description": "A warm local stay near Lovran old town.",
                "welcome_message": "Welcome to Lovran.",
                "local_specialties": ["Gastronomy", "Lungomare walks"],
            },
        }

    monkeypatch.setattr(HostOnboardingService, "get_host_profile", fake_host_profile)
    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", alternate_structured_response)

    response = await async_client.post(
        "/api/v1/onboarding/accommodation/ai-enhance",
        headers=host_token_headers,
        json={
            "current_data": {
                "property_name": "Ben Host Stay Lovran",
                "property_type": "apartment",
                "location_story": "",
                "max_guests": 12,
                "amenities": [],
                "services_offered": [],
                "expertise_areas": [],
                "city": "Lovran",
                "county": "Kvarner",
            },
            "enhancement_type": "comprehensive",
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["enhanced_content"]["description"] == "A warm local stay near Lovran old town."
    assert body["enhanced_content"]["amenities"]
    assert body["enhanced_content"]["services"]
    assert body["enhanced_content"]["specialties"] == ["Gastronomy", "Lungomare walks"]

