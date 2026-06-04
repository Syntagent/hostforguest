"""Source-level checks for compliance dashboard tab wiring."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_tabs_include_compliance():
    src = (PROJECT_ROOT / "frontend/src/components/dashboard/dashboard-tabs.ts").read_text()
    assert '"compliance"' in src
    assert "obveze" in src
    assert 'compliance: "Compliance"' in src


def test_host_dashboard_nav_and_main_content():
    host_src = (PROJECT_ROOT / "frontend/src/components/dashboard/host-dashboard.tsx").read_text()
    main_src = (
        PROJECT_ROOT / "frontend/src/components/dashboard/widgets/host-dashboard-main-content.tsx"
    ).read_text()
    assert 'id: "compliance"' in host_src
    assert 'label: "Compliance"' in host_src
    assert "ComplianceTab" in main_src
    assert 'activeTab === "compliance"' in main_src
    assert "onNavigateTab" in main_src


def test_compliance_tab_includes_novasol_panel():
    tab_src = (PROJECT_ROOT / "frontend/src/components/dashboard/compliance/compliance-tab.tsx").read_text()
    yaml_src = (PROJECT_ROOT / "infra/compliance/obligations.hr.yaml").read_text()
    assert "ComplianceNovasolPanel" in tab_src
    assert "novasol" in tab_src
    assert 'id: novasol' in yaml_src
