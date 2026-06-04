"""Guest-facing recommendation copy filters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_guest_recommendation_display_module():
    src = (ROOT / "frontend" / "src" / "components" / "guest" / "guest-recommendation-display.ts").read_text()
    assert "HIDDEN_FACTOR_RE" in src
    assert "guestFacingReason" in src
    assert "isGuestVisibleRecommendation" in src


def test_recommendation_service_hides_internal_factors():
    src = (ROOT / "app" / "services" / "recommendation_service.py").read_text()
    assert "_INTERNAL_FACTOR_KEYS" in src
    assert "_is_guest_visible_attraction" in src
    assert "enrich_list_for_guest" in src
    assert "if att is not None and not self._is_guest_visible_attraction(att):" in src
