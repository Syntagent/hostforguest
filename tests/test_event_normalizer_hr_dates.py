"""Croatian date parsing for event normalizer."""

from datetime import datetime, timezone

from app.scraping.events.normalizer import parse_hr_date_range


def test_dd_mm_yyyy_range():
    start, end = parse_hr_date_range("10.10.2026 – 12.10.2026")
    assert start == datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


def test_single_dd_mm_yyyy():
    start, end = parse_hr_date_range("15.4.2026")
    assert start and start.month == 4 and start.day == 15
    assert end == start
