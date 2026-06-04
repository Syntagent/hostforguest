"""Event timing parsing, overlap, and guest inclusion rules."""

from datetime import date, datetime, timezone

from app.scraping.events.normalizer import parse_hr_date_range, parse_time_from_text
from app.services.event_timing_utils import (
    format_event_schedule_label,
    infer_dates_from_blob,
    is_event_past,
    overlaps_stay_window,
    should_include_event_for_guest,
    text_suggests_past_event,
)


def test_parse_time_from_croatian_copy():
    assert parse_time_from_text("Koncert u 19.30 h") == parse_time_from_text("19:30")
    assert parse_time_from_text("Početak u 18:00 sati").hour == 18


def test_parse_hr_date_range_with_time():
    start, end = parse_hr_date_range("15.10.2026 u 18:00")
    assert start is not None
    assert start.hour == 18
    assert start.minute == 0


def test_infer_dates_from_title():
    start, end = infer_dates_from_blob("Marunada 10.10.2026 – 12.10.2026", "")
    assert start is not None
    assert start.day == 10
    assert end is not None
    assert end.day == 12


def test_past_event_excluded():
    assert is_event_past(end_date=date(2024, 1, 1), today=date(2026, 6, 1))
    assert text_suggests_past_event("Festival 2023", "summer fun", today=date(2026, 6, 1))


def test_overlaps_stay_window():
    assert overlaps_stay_window(
        date(2026, 6, 5),
        date(2026, 6, 7),
        date(2026, 6, 1),
        date(2026, 6, 10),
    )
    assert not overlaps_stay_window(
        date(2026, 12, 1),
        date(2026, 12, 5),
        date(2026, 6, 1),
        date(2026, 6, 10),
    )


def test_should_include_during_stay():
    include, certainty = should_include_event_for_guest(
        start_date=date(2026, 6, 5),
        end_date=date(2026, 6, 6),
        title="Local market",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 10),
        today=date(2026, 5, 20),
    )
    assert include
    assert certainty in ("date_only", "exact", "inferred", "unknown")


def test_should_exclude_past_and_stale_undated():
    include, _ = should_include_event_for_guest(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 2),
        title="Old fest",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 10),
        today=date(2026, 6, 1),
    )
    assert not include

def test_classify_near_stay_before_check_in():
    from app.services.event_timing_utils import classify_stay_timing

    score, status = classify_stay_timing(
        date(2026, 5, 31),
        date(2026, 5, 31),
        date(2026, 6, 5),
        date(2026, 6, 12),
    )
    assert status == "near_stay"
    assert score >= 0.7


def test_should_exclude_undated_even_if_recently_scraped():
    include, certainty = should_include_event_for_guest(
        title="Koncert bez datuma",
        description="Samo naslov",
        scraped_at=datetime.now(timezone.utc),
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 10),
        today=date(2026, 6, 1),
    )
    assert not include
    assert certainty == "unknown"


def test_schedule_label_includes_time():
    label = format_event_schedule_label(
        start_at=datetime(2026, 10, 10, 18, 30, tzinfo=timezone.utc),
        end_at=datetime(2026, 10, 10, 21, 0, tzinfo=timezone.utc),
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 10),
    )
    assert label is not None
    assert "18:30" in label
