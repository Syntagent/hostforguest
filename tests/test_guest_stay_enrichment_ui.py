"""Frontend regression checks for enriched guest guide."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")


def test_guest_guide_has_stay_tab_and_assistant():
    source = read_frontend("components/guest/guest-interface.tsx")
    assert '{ id: "stay", label: "Your stay"' in source
    assert "GuestStayTab" in source
    assert "GuestTodayStrip" in source
    assert "GuestAssistantFab" in source
    assert "GuestMessageFab" not in source


def test_guest_stay_tab_covers_rules_and_emergency():
    source = read_frontend("components/guest/guest-stay-tab.tsx")
    assert 'data-testid="guest-stay-tab"' in source
    assert "property_rules" in source or "GuestPropertyRules" in source
    assert "Emergency" in source
    assert "wifiPassword" in source or "WiFi" in source


def test_accommodation_tab_persists_property_rules_to_profile():
    source = read_frontend("components/dashboard/accommodation-tab.tsx")
    assert "property_rules: propertyRules" in source
    assert "profile?.property_rules" in source


def test_legacy_guest_dashboard_removed():
    assert not (ROOT / "frontend" / "src" / "components/guest/GuestDashboard.tsx").exists()
