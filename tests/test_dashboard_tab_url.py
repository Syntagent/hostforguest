"""Contract tests for host dashboard ?tab= URL sync."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TABS = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "dashboard-tabs.ts"
USE_HOOK = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "use-dashboard-tab-url.ts"
HOST_DASHBOARD = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "host-dashboard.tsx"
ACCOMMODATION_TAB = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "accommodation-tab.tsx"
ACCOMMODATION_AGENT_DIR = REPO_ROOT / "frontend" / "src" / "components" / "dashboard" / "accommodation-ai-agent"
PW_HELPER = REPO_ROOT / "tests" / "e2e" / "dashboard-tab-url.ts"


def test_dashboard_tab_url_module_exports_parser_and_aliases() -> None:
    text = DASHBOARD_TABS.read_text(encoding="utf-8")
    assert "parseDashboardTabParam" in text
    assert "buildDashboardTabHref" in text
    assert 'stay: "accommodation"' in text
    assert 'guests: "groups"' in text


def test_host_dashboard_uses_tab_url_hook() -> None:
    text = HOST_DASHBOARD.read_text(encoding="utf-8")
    assert "useDashboardTabUrl" in text
    assert "selectTab" in text
    assert "setActiveTab(id as DashboardTab)" not in text


def test_dashboard_client_wraps_suspense_for_search_params() -> None:
    client = REPO_ROOT / "frontend" / "src" / "app" / "dashboard" / "dashboard-client.tsx"
    text = client.read_text(encoding="utf-8")
    assert "Suspense" in text
    assert "use-dashboard-tab-url" not in text


def test_playwright_dashboard_tab_url_helper_maps_stay() -> None:
    text = PW_HELPER.read_text(encoding="utf-8")
    assert 'Stay: "accommodation"' in text
    assert "dashboardPathForTab" in text


def test_accommodation_agent_files_are_extracted() -> None:
    dashboard_text = HOST_DASHBOARD.read_text(encoding="utf-8")
    assert "AccommodationAgentTab" in dashboard_text
    assert ACCOMMODATION_TAB.exists()
    assert (ACCOMMODATION_AGENT_DIR / "accommodation-ai-agent-panel.tsx").exists()
    assert (ACCOMMODATION_AGENT_DIR / "accommodation-checklist.ts").exists()
    assert (ACCOMMODATION_AGENT_DIR / "agent-composer.tsx").exists()
