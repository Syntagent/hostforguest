"""Guest-facing distance label helpers (mirrors frontend guest-distance.ts)."""

from __future__ import annotations

import math


def format_guest_distance_km(km: float | None) -> str | None:
    if km is None or not math.isfinite(km):
        return None
    rounded = round(km * 10) / 10 if km < 10 else round(km)
    return f"~{rounded} km"


def guest_distance_hint(km: float | None) -> str | None:
    if km is None or not math.isfinite(km):
        return None
    if km <= 3:
        return "Short trip from your stay"
    if km <= 8:
        return "Easy half-day outing"
    if km <= 20:
        return "Plan a half-day trip"
    if km <= 40:
        return "Worth a day trip"
    return "Further afield — check travel time"


def format_guest_distance_label(km: float | None) -> str | None:
    dist = format_guest_distance_km(km)
    if not dist:
        return None
    hint = guest_distance_hint(km)
    return f"{dist} · {hint}" if hint else dist


def test_format_guest_distance_label_near_stay():
    label = format_guest_distance_label(2.0)
    assert label == "~2.0 km · Short trip from your stay"


def test_format_guest_distance_label_half_day():
    label = format_guest_distance_label(6.5)
    assert label == "~6.5 km · Easy half-day outing"


def test_format_guest_distance_label_far():
    label = format_guest_distance_label(35)
    assert label == "~35 km · Worth a day trip"
