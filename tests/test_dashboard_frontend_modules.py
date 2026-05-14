"""Ensure extracted host dashboard modules stay present (refactor guard)."""
from pathlib import Path


def test_dashboard_tab_and_modal_modules_exist():
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "dashboard"
    required = [
        "dashboard-types.ts",
        "overview-tab.tsx",
        "guest-groups-tab.tsx",
        "attractions-tab.tsx",
        "group-modals.tsx",
        "delete-attraction-modal.tsx",
        "insights-tab.tsx",
    ]
    missing = [name for name in required if not (base / name).is_file()]
    assert not missing, f"Missing dashboard modules: {missing}"
