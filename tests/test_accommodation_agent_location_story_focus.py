"""Property-story instructions must not land in property_name when focus was wrong."""

import pytest
from httpx import AsyncClient

from app.services.host_onboarding_service import HostOnboardingService


def test_resolve_focus_from_message_detects_property_story():
    svc = HostOnboardingService(db=None)  # type: ignore[arg-type]
    assert (
        svc._resolve_focused_item_from_message(
            "in property story i want to emphasize Nature and closeness to sea and Učka mountain",
            "property_name",
        )
        == "location_story"
    )


def test_draft_location_story_weaves_nature_sea_ucka():
    svc = HostOnboardingService(db=None)  # type: ignore[arg-type]
    existing = (
        "Our property is embraced by the stunning natural landscapes of Lovran, "
        "a true paradise for nature lovers."
    )
    instruction = "in property story i want to emphasize Nature and closeness to sea and Učka mountain"
    draft = svc._draft_location_story_update(
        existing=existing,
        instruction=instruction,
        city="Lovran",
        property_type="apartment",
    )
    lower = draft.lower()
    assert "nature" in lower or "natural" in lower
    assert "sea" in lower or "adriatic" in lower
    assert "učka" in lower or "ucka" in lower
    assert len(draft) > 80


@pytest.mark.asyncio
async def test_agent_story_message_while_focused_property_name_uses_location_story(
    async_client: AsyncClient,
    host_token_headers: dict[str, str],
):
    """Regression: narrative about property story must not become property_name patch."""
    response = await async_client.post(
        "/api/v1/onboarding/accommodation/agent/message",
        headers=host_token_headers,
        json={
            "message": "in property story i want to emphasize Nature and closeness to sea and Učka mountain",
            "focused_item_id": "property_name",
            "checklist_state": [{"id": "property_name", "status": "in_progress"}],
            "accommodation_snapshot": {
                "city": "Lovran",
                "property_type": "apartment",
                "property_name": "Ben Host Stay Lovran",
                "location_story": (
                    "Our property is embraced by the stunning natural landscapes of Lovran, "
                    "a true paradise for nature lovers."
                ),
            },
            "conversation_history": [],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    patch = body.get("suggested_patch") or {}
    assert patch.get("location_story")
    assert "property_name" not in patch or patch.get("property_name") != (
        "in property story i want to emphasize Nature and closeness to sea and Učka mountain"
    )
