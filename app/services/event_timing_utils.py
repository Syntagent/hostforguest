"""Event date/time parsing, overlap checks, and guest-facing schedule labels."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional, Tuple

from app.scraping.events.normalizer import parse_hr_date_range, parse_time_from_text

DateCertainty = Literal["exact", "date_only", "inferred", "unknown"]

_PAST_YEAR_HINT = re.compile(r"\b(20\d{2})\b")


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def infer_dates_from_blob(title: str, description: str = "") -> Tuple[Optional[datetime], Optional[datetime]]:
    """Best-effort date range from Croatian event copy."""
    blob = f"{title} {description}".strip()
    if not blob:
        return None, None
    start, end = parse_hr_date_range(blob)
    if not start and not end:
        return None, None
    t = parse_time_from_text(blob)
    if start and t:
        start = start.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    if end and t and (not start or end.date() == start.date()):
        end = end.replace(hour=min(23, t.hour + 2), minute=t.minute, second=0, microsecond=0)
    return start, end or start


def effective_event_window(
    *,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    title: str = "",
    description: str = "",
) -> Tuple[Optional[date], Optional[date], Optional[datetime], Optional[datetime], DateCertainty]:
    """Normalize DB/API fields into dates + datetimes with certainty."""
    certainty: DateCertainty = "unknown"
    sdt = start_at
    edt = end_at
    if not sdt and start_date:
        sdt = datetime.combine(start_date, time(12, 0), tzinfo=timezone.utc)
        certainty = "date_only"
    if not edt and end_date:
        edt = datetime.combine(end_date, time(23, 59), tzinfo=timezone.utc)
    if sdt and certainty == "unknown":
        certainty = "exact" if (sdt.hour or sdt.minute) else "date_only"

    if not sdt:
        inferred_start, inferred_end = infer_dates_from_blob(title, description)
        if inferred_start:
            sdt = inferred_start
            edt = edt or inferred_end
            certainty = "inferred"

    sd = sdt.date() if sdt else start_date
    ed = edt.date() if edt else (end_date or sd)
    return sd, ed, sdt, edt, certainty


def is_event_past(
    *,
    end_date: Optional[date],
    end_at: Optional[datetime] = None,
    today: Optional[date] = None,
) -> bool:
    today = today or date.today()
    use_realtime = today == date.today()
    if end_at:
        end_d = end_at.date()
        if end_at.tzinfo and use_realtime:
            now = datetime.now(timezone.utc)
            if end_at < now - timedelta(hours=6):
                return True
        elif end_d < today:
            return True
        return end_d < today
    if end_date and end_date < today:
        return True
    return False


def overlaps_stay_window(
    start: Optional[date],
    end: Optional[date],
    check_in: Optional[date],
    check_out: Optional[date],
    *,
    grace_before_days: int = 7,
    grace_after_days: int = 21,
) -> bool:
    if not check_in and not check_out:
        return True
    if not start and not end:
        return False
    cin = check_in or check_out
    cout = check_out or check_in
    if not cin or not cout:
        return True
    win_start = cin - timedelta(days=grace_before_days)
    win_end = cout + timedelta(days=grace_after_days)
    ev_start = start or end
    ev_end = end or start
    if not ev_start or not ev_end:
        return False
    return not (ev_end < win_start or ev_start > win_end)


def text_suggests_past_event(title: str, description: str, today: Optional[date] = None) -> bool:
    """Heuristic: explicit year in copy is before current year."""
    today = today or date.today()
    blob = f"{title} {description}"
    years = [int(y) for y in _PAST_YEAR_HINT.findall(blob)]
    if not years:
        return False
    return max(years) < today.year


StayTimingStatus = Literal["during_stay", "near_stay", "outside_stay", "upcoming", "unknown"]


def classify_stay_timing(
    start: Optional[date],
    end: Optional[date],
    check_in: Optional[date],
    check_out: Optional[date],
    *,
    grace_before_days: int = 7,
    grace_after_days: int = 7,
) -> Tuple[float, StayTimingStatus]:
    """Score + guest-facing timing bucket for stay recommendations."""
    if not start and not end:
        return 0.25, "unknown"
    if not check_in and not check_out:
        return (0.55, "upcoming") if start else (0.35, "unknown")

    ev_start = start or end
    ev_end = end or start
    cin = check_in or check_out
    cout = check_out or check_in
    if not ev_start or not ev_end or not cin or not cout:
        return 0.45, "upcoming"

    if not (ev_end < cin or ev_start > cout):
        return 1.0, "during_stay"

    grace_start = cin - timedelta(days=grace_before_days)
    if ev_end < cin and ev_end >= grace_start:
        return 0.72, "near_stay"

    grace_end = cout + timedelta(days=grace_after_days)
    if ev_start > cout and ev_start <= grace_end:
        return 0.68, "near_stay"

    return 0.12, "outside_stay"


def should_include_event_for_guest(
    *,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    title: str = "",
    description: str = "",
    scraped_at: Optional[datetime] = None,
    check_in: Optional[date] = None,
    check_out: Optional[date] = None,
    today: Optional[date] = None,
) -> Tuple[bool, DateCertainty]:
    today = today or date.today()
    sd, ed, sdt, edt, certainty = effective_event_window(
        start_at=start_at,
        end_at=end_at,
        start_date=start_date,
        end_date=end_date,
        title=title,
        description=description,
    )

    if text_suggests_past_event(title, description, today):
        return False, certainty

    if is_event_past(end_date=ed, end_at=edt, today=today):
        return False, certainty

    if sd or ed:
        if check_in or check_out:
            if not overlaps_stay_window(sd, ed, check_in, check_out):
                return False, certainty
        return True, certainty

    return False, "unknown"


def format_event_schedule_label(
    *,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    title: str = "",
    description: str = "",
) -> Optional[str]:
    sd, ed, sdt, edt, certainty = effective_event_window(
        start_at=start_at,
        end_at=end_at,
        start_date=start_date,
        end_date=end_date,
        title=title,
        description=description,
    )
    if not sd and not sdt:
        return None

    def _fmt_date(d: date) -> str:
        return f"{d.day} {d.strftime('%b %Y')}"

    def _fmt_time(dt: Optional[datetime]) -> Optional[str]:
        if not dt or (dt.hour == 12 and dt.minute == 0 and certainty == "date_only"):
            return None
        if dt.hour == 0 and dt.minute == 0:
            return None
        return dt.strftime("%H:%M")

    start_label = _fmt_date(sd) if sd else None
    end_label = _fmt_date(ed) if ed and ed != sd else None
    start_time = _fmt_time(sdt)
    end_time = _fmt_time(edt)

    if start_label and end_label:
        base = f"{start_label} – {end_label}"
    elif start_label:
        base = start_label
    else:
        return None

    if start_time and end_time and start_time != end_time:
        return f"{base} · {start_time}–{end_time}"
    if start_time:
        return f"{base} · from {start_time}"
    if certainty == "unknown":
        return f"{base} · date TBC — confirm with host"
    return base
