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
    assert "prefers-reduced-motion: reduce" in source


def test_guest_setup_loading_and_invalid_code_are_actionable():
    source = read_frontend("components/guest/GuestOnboardingWizard.tsx")

    assert "Checking your invitation" in source
    assert "Try another code" in source
    assert "Wrong code? Enter a different one" in source
    assert "aria-live=\"polite\"" in source


def test_guest_setup_page_prevents_mobile_overflow():
    source = read_frontend("app/guest/setup/[accessCode]/page.tsx")

    assert "overflow-x-hidden" in source


def test_guest_dashboard_redirects_to_canonical_guide():
    source = read_frontend("app/guest/dashboard/page.tsx")

    assert "guest_access_code" in source
    assert "router.replace(code ? `/guest/${code}` : \"/guest/join\")" in source
    assert "components/guest/GuestDashboard" not in source
    assert "contexts/guest-context" not in source
    assert "<GuestDashboard" not in source
    assert "<GuestProvider" not in source


def test_legacy_guest_preferences_code_route_redirects_to_setup():
    source = read_frontend("app/guest/preferences/[accessCode]/page.tsx")

    assert "GuestPreferencesCodePage" in source
    assert "router.replace(code ? `/guest/setup/${code}` : \"/guest/join\")" in source
    assert "Legacy URL" in source


def test_guest_setup_updates_existing_preferences_instead_of_duplicating():
    source = read_frontend("components/guest/GuestOnboardingWizard.tsx")

    assert "setExistingPreference(latestPreference)" in source
    assert "You&apos;re updating your preferences" in source
    assert "splitGuestName(latestPreference.guest_name)" in source
    assert "parseMobilityNotes(latestPreference.mobility_notes)" in source
    assert "existingPreference?.id" in source
    assert "guestGroupsApi.updateGuestPreference(accessCode, existingPreference.id, preferencePayload)" in source
    assert "guestGroupsApi.addGuestPreference(accessCode, preferencePayload)" in source


def test_guest_setup_has_field_level_validation_and_clearer_budget_labels():
    source = read_frontend("components/guest/GuestOnboardingWizard.tsx")

    assert "type StepOneField" in source
    assert "const [stepOneErrors" in source
    assert "validateStepOne()" in source
    assert 'aria-invalid={stepOneErrors.firstName ? "true" : "false"}' in source
    assert 'aria-describedby={stepOneErrors.email ? "g-email-error" : undefined}' in source
    assert "clearStepOneError(\"terms\")" in source
    assert "{BUDGET_LABELS[b]}" in source
    assert "Please fix the highlighted fields to continue." in source


def test_guest_guide_loads_critical_content_before_optional_sections():
    source = read_frontend("components/guest/guest-interface.tsx")

    assert "contentWarning" in source
    assert "criticalGuideLoaded" in source
    assert "setLoading(false);" in source
    assert "Some guide suggestions could not refresh" in source
    assert "Try again" in source
    assert '{ id: "recommendations", label: "Discover"' in source
    assert '{ id: "itinerary", label: "Plan"' in source
    assert '{ id: "events", label: "Events"' in source
    assert '{ id: "stay", label: "Your stay"' in source
    fab = read_frontend("components/guest/guest-assistant-fab.tsx")
    assert "bottom-[calc(6rem+env(safe-area-inset-bottom))]" in fab


def test_guest_guide_prominently_displays_stay_dates():
    source = read_frontend("components/guest/guest-interface.tsx")

    assert "function stayDateSummary" in source
    assert "Stay dates" in source
    assert "Check-in" in source
    assert "Check-out" in source
    assert "stayDates.range" in source
    assert "stayDates.nights" in source
    assert "aria-labelledby=\"guest-stay-dates\"" in source
    assert "outD.getDate()" in source

