"""Croatian date parsing and draft normalization."""

from __future__ import annotations

import re
from datetime import datetime, time, timezone
from typing import Optional, Tuple

_MONTHS_HR = {
    "siječanj": 1,
    "sijecnja": 1,
    "veljača": 2,
    "veljace": 2,
    "ožujak": 3,
    "ozujak": 3,
    "travanj": 4,
    "svibanj": 5,
    "lipanj": 6,
    "srpanj": 7,
    "kolovoz": 8,
    "rujan": 9,
    "listopad": 10,
    "studeni": 11,
    "prosinac": 12,
}


def parse_hr_date_range(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse Croatian date strings from event text.

    Supports: 15.6.2026, 15.06.2026 – 18.06.2026, od 15. do 18. lipnja 2026
    """
    if not text or not str(text).strip():
        return None, None

    raw = str(text).strip().lower()
    raw = raw.replace("–", "-").replace("—", "-")

    # DD.MM.YYYY - DD.MM.YYYY
    range_match = re.search(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
        raw,
    )
    if range_match:
        d1, m1, y1, d2, m2, y2 = range_match.groups()
        start = _dt(int(y1), int(m1), int(d1))
        end = _dt(int(y2), int(m2), int(d2))
        return _apply_time_from_text(text, start, end)

    # Single DD.MM.YYYY
    single = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
    if single:
        d, m, y = single.groups()
        start = _dt(int(y), int(m), int(d))
        return _apply_time_from_text(text, start, start)

    # YYYY-MM-DD
    iso = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", raw)
    if iso:
        y, m, d = iso.groups()
        start = _dt(int(y), int(m), int(d))
        return _apply_time_from_text(text, start, start)

    # od 15. do 18. lipnja 2026
    od_do = re.search(
        r"od\s+(\d{1,2})\.\s*do\s+(\d{1,2})\.\s*([a-zčćžšđ]+)\s+(\d{4})",
        raw,
    )
    if od_do:
        d1, d2, month_name, year = od_do.groups()
        month = _MONTHS_HR.get(month_name.replace("č", "c").replace("ć", "c"), None)
        if month:
            start = _dt(int(year), month, int(d1))
            end = _dt(int(year), month, int(d2))
            return _apply_time_from_text(text, start, end)

    return None, None



def parse_time_from_text(text: str) -> Optional[time]:
    if not text:
        return None
    raw = str(text)
    patterns = [
        r"\bu\s+(\d{1,2})[:.](\d{2})\s*(?:h|sat|sati)?",
        r"(?<!\d\.)(?<!\d)(\d{1,2}):(\d{2})(?!\.\d)\s*(?:h|sat|sati)?",
        r"(?<!\d\.)(?<!\d)(\d{1,2})\.(\d{2})\s*(?:h|sat|sati)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw, re.IGNORECASE)
        if not m:
            continue
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            continue
        return time(hour, minute)
    return None


def _apply_time_from_text(
    text: str, start: datetime, end: Optional[datetime]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    t = parse_time_from_text(text)
    if not t:
        return start, end
    start = start.replace(hour=t.hour, minute=t.minute)
    if end and end.date() == start.date():
        end = end.replace(hour=min(23, t.hour + 2), minute=t.minute)
    return start, end


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


def infer_tags(text: str) -> list[str]:
    blob = (text or "").lower()
    tags: list[str] = []
    mapping = {
        "festival": ("festival", "manifestacija", "fešta", "festa"),
        "music": ("koncert", "music", "glazba"),
        "gastro": ("gastro", "wine", "vino", "truffle", "tasting"),
        "market": ("market", "tržnica", "trznica", "sajam"),
        "culture": ("kultura", "cultural", "izložba", "izlozba"),
        "sport": ("sport", "regatta", "utrka"),
    }
    for tag, hints in mapping.items():
        if any(h in blob for h in hints):
            tags.append(tag)
    return tags
