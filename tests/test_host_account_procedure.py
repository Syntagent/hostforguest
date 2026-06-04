"""Host sign-in vs onboarding procedure is documented in the UI."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = REPO_ROOT / "frontend" / "src" / "app" / "login" / "page.tsx"
PROCEDURE = REPO_ROOT / "frontend" / "src" / "lib" / "host-account-procedure.ts"
ONBOARDING_PAGE = REPO_ROOT / "frontend" / "src" / "app" / "onboarding" / "page.tsx"
DASHBOARD = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "host-dashboard.tsx"


def test_login_page_explains_host_access_procedure() -> None:
    text = LOGIN_PAGE.read_text(encoding="utf-8")
    assert "How host access works" in text
    assert "HOST_ACCESS_PROCEDURE" in text
    assert "Required before you can sign in" in text
    assert "isHostProfileReady" in text


def test_procedure_module_defines_profile_readiness() -> None:
    text = PROCEDURE.read_text(encoding="utf-8")
    assert "isHostProfileReady" in text
    assert "onboarding_completed" in text
    assert "HOST_ACCESS_PROCEDURE" in text


def test_onboarding_shows_continue_after_login_banner() -> None:
    text = ONBOARDING_PAGE.read_text(encoding="utf-8")
    assert 'from") === "login"' in text
    assert "Complete your host profile" in text


def test_dashboard_warns_when_profile_incomplete() -> None:
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "Property profile incomplete" in text
    assert "isHostProfileReady" in text
