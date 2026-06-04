"""Stay dates in guest group create/list UI."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")


def test_create_group_modal_has_stay_schedule():
    source = read_frontend("components/dashboard/group-modals.tsx")
    assert "Stay schedule" in source
    assert "check_in_date" in source
    assert "check_out_date" in source
    assert "Arrival (check-in)" in source
    assert "Departure (check-out)" in source


def test_guest_groups_tab_sorted_by_stay():
    source = read_frontend("components/dashboard/guest-groups-tab.tsx")
    assert "sortGuestGroupsByStay" in source
    assert "Arrives" in source
    assert "Leaves" in source
    assert "Sorted by arrival date" in source
    assert "onDeleteGroup" in source


def test_host_dashboard_sends_stay_dates_on_create():
    source = read_frontend("components/dashboard/host-dashboard.tsx")
    assert "dateInputToCheckInIso" in source
    assert "validateStayDates" in source
    assert "check_in_date:" in source


def test_guest_group_stay_helpers():
    stay = read_frontend("components/dashboard/guest-group-stay.ts")
    assert "sortGuestGroupsByStay" in stay
    assert "validateStayDates" in stay
    assert "defaultStayDateStrings" in stay
