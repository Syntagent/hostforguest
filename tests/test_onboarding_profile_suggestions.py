"""Contract tests for onboarding profile suggestion fallbacks."""

from __future__ import annotations

from app.services.host_onboarding_service import HostOnboardingService


def test_rule_based_profile_suggestions_match_ui_contract() -> None:
    service = object.__new__(HostOnboardingService)
    suggestions = service._rule_based_profile_suggestions(
        {
            "location": {"city": "Lovran"},
            "host": {
                "first_name": "E2E",
                "location_story": "I guide guests to local coves and konobas.",
                "property_name": "Villa E2E Full Lovran",
            },
        }
    )

    required_ui_fields = {
        "business_description",
        "welcome_message",
        "host_story",
        "local_specialties",
        "experience_promise",
    }
    assert required_ui_fields.issubset(suggestions)
    assert all(suggestions[field] for field in required_ui_fields)
