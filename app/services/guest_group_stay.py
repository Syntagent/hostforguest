"""Stay window helpers for guest groups (aligned with dashboard frontend)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Union

from app.models.guest_group import GuestGroup


class StayPhase(str, Enum):
    UPCOMING = "upcoming"
    IN_HOUSE = "in_house"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


def _as_datetime(value: object) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _calendar_day(dt: object) -> Optional[datetime]:
    parsed = _as_datetime(dt)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return datetime(parsed.year, parsed.month, parsed.day)


def get_stay_phase(
    group: Union[GuestGroup, object],
    *,
    today: Optional[datetime] = None,
) -> StayPhase:
    """Calendar-day stay phase (check-in through check-out inclusive)."""
    check_in = getattr(group, "check_in_date", None)
    check_out = getattr(group, "check_out_date", None)
    if not check_in or not check_out:
        return StayPhase.UNKNOWN
    start = _calendar_day(check_in)
    end = _calendar_day(check_out)
    if not start or not end:
        return StayPhase.UNKNOWN
    now = _calendar_day(today or datetime.now(timezone.utc))
    if now < start:
        return StayPhase.UPCOMING
    if now > end:
        return StayPhase.COMPLETED
    return StayPhase.IN_HOUSE


def is_in_stay(group: Union[GuestGroup, object], *, today: Optional[datetime] = None) -> bool:
    return get_stay_phase(group, today=today) == StayPhase.IN_HOUSE
