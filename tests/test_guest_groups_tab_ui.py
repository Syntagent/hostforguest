"""Regression checks for dashboard Guest Groups tab UI."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")


def test_guest_groups_tab_empty_state_and_mobile_actions():
    source = read_frontend("components/dashboard/guest-groups-tab.tsx")
    assert "No guest groups yet" in source
    assert "Create New Group" in source
    assert "guestGroups.length > 0" in source or "guestGroups.length === 0" in source
    assert "flex-col gap-2 sm:flex-row" in source


def test_group_modals_stack_above_bottom_nav():
    source = read_frontend("components/dashboard/group-modals.tsx")
    assert "z-[70]" in source
    assert "safe-area-inset-bottom" in source
    assert "document.body.style.overflow" in source


def test_create_group_trims_name_before_api():
    source = read_frontend("components/dashboard/host-dashboard.tsx")
    assert "guestGroupsApi.create" in source
    assert 'group_name?.trim()' in source or "group_name?.trim()" in source
