"""Regression checks for guest-facing mobile setup polish."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")


def test_guest_setup_wizard_keeps_mobile_actions_visible():
    source = read_frontend("components/guest/GuestOnboardingWizard.tsx")

    assert "sticky bottom-0" in source
    assert "overflow-x-hidden" in source
    assert "Open guide" in source
    assert "ChevronRight" in source
    assert "max-h-[min(58vh,28rem)]" in source
    assert "overflow-x-auto" in source
    assert "rows={2}" in source


def test_guest_setup_loading_and_invalid_code_are_actionable():
    source = read_frontend("components/guest/GuestOnboardingWizard.tsx")

    assert "Checking your invitation" in source
    assert "Try another code" in source
    assert "Wrong code? Enter a different one" in source
    assert "aria-live=\"polite\"" in source


def test_guest_setup_page_prevents_mobile_overflow():
    source = read_frontend("app/guest/setup/[accessCode]/page.tsx")

    assert "overflow-x-hidden" in source

