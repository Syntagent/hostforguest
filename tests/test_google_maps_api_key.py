"""
Google Maps / Google AI key checks — optional when env vars are set (local .env).

CI and fresh clones typically omit these keys; tests skip instead of failing.
"""

import os
import pytest


requires_maps_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"),
    reason="GOOGLE_MAPS_API_KEY not set (optional local check)",
)


requires_google_ai_key = pytest.mark.skipif(
    not os.getenv("GOOGLE_AI_API_KEY"),
    reason="GOOGLE_AI_API_KEY not set (optional local check)",
)


@requires_maps_key
def test_google_maps_api_key_configured():
    """When set, Google Maps API key looks plausible."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    assert api_key.strip() != "", "GOOGLE_MAPS_API_KEY is empty"

    assert api_key.startswith("AIza"), (
        f"Google Maps API key should start with 'AIza', got: {api_key[:10]}..."
    )

    assert len(api_key) > 30, f"Google Maps API key seems too short: {len(api_key)} characters"


@requires_google_ai_key
def test_google_ai_api_key_configured():
    """When set, Google AI API key looks plausible."""
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")

    assert api_key.strip() != "", "GOOGLE_AI_API_KEY is empty"

    assert api_key.startswith("AIza"), (
        f"Google AI API key should start with 'AIza', got: {api_key[:10]}..."
    )


@requires_maps_key
@requires_google_ai_key
def test_environment_variables_loaded():
    """Both keys present when this combined check runs."""
    assert os.getenv("GOOGLE_MAPS_API_KEY")
    assert os.getenv("GOOGLE_AI_API_KEY")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
