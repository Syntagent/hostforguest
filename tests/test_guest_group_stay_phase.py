"""Stay phase counting for dashboard analytics."""

from datetime import datetime

from app.services.guest_group_stay import StayPhase, get_stay_phase, is_in_stay


class _Group:
    def __init__(self, check_in, check_out):
        self.check_in_date = check_in
        self.check_out_date = check_out


def test_in_stay_on_check_in_day():
    g = _Group(
        datetime(2026, 5, 28, 15, 0),
        datetime(2026, 6, 4, 10, 0),
    )
    assert get_stay_phase(g, today=datetime(2026, 5, 28, 12, 0)) == StayPhase.IN_HOUSE
    assert is_in_stay(g, today=datetime(2026, 5, 28, 12, 0))


def test_upcoming_before_check_in():
    g = _Group(
        datetime(2026, 5, 28, 15, 0),
        datetime(2026, 6, 4, 10, 0),
    )
    assert get_stay_phase(g, today=datetime(2026, 5, 27, 12, 0)) == StayPhase.UPCOMING
    assert not is_in_stay(g, today=datetime(2026, 5, 27, 12, 0))


def test_completed_after_check_out():
    g = _Group(
        datetime(2026, 5, 28, 15, 0),
        datetime(2026, 6, 4, 10, 0),
    )
    assert get_stay_phase(g, today=datetime(2026, 6, 5, 12, 0)) == StayPhase.COMPLETED
    assert not is_in_stay(g, today=datetime(2026, 6, 5, 12, 0))
