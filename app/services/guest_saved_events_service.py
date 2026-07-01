"""Persist guest-saved event ideas on the guest group (JSON blob)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_group import GuestGroup

logger = logging.getLogger(__name__)

SAVED_EVENTS_KEY = "_saved_events_v1"

NON_GUEST_SAVED_PATTERNS = (
    "qa event",
    "test seasonal",
    "host-visible-",
    "saved-only-",
)

_GUEST_SAVED_EVENT_KEYS = frozenset(
    {
        "event_id",
        "title",
        "description",
        "start_date",
        "end_date",
        "start_time",
        "end_time",
        "schedule_label",
        "event_type",
        "cities",
        "regions",
        "url",
        "plan_hint",
        "distance_km",
        "venue_name",
        "booking_required",
        "admission_info",
        "why_recommended",
        "saved_at",
        "preferred_day_number",
        "preferred_day_plan_id",
        "preferred_day_title",
        "itinerary_activity_id",
        "itinerary_day_plan_id",
        "itinerary_activity_title",
        "itinerary_activity_start_time",
        "itinerary_activity_end_time",
        "guest_action",
        "guest_note",
        "guest_action_at",
        "host_status",
        "host_action_at",
        "host_note",
    }
)

_GUEST_SAVED_EVENT_WRITE_KEYS = _GUEST_SAVED_EVENT_KEYS - {
    "itinerary_activity_id",
    "itinerary_day_plan_id",
    "itinerary_activity_title",
    "itinerary_activity_start_time",
    "itinerary_activity_end_time",
    "guest_action_at",
    "host_status",
    "host_action_at",
    "host_note",
}

_HOST_SAVED_EVENT_PATCH_KEYS = _GUEST_SAVED_EVENT_WRITE_KEYS | {
    "host_status",
    "host_action_at",
    "host_note",
}


_GUEST_SAVED_EVENT_TEXT_KEYS = frozenset(
    {
        "event_id",
        "title",
        "description",
        "distance_km",
        "url",
        "plan_hint",
        "venue_name",
        "admission_info",
        "why_recommended",
        "schedule_label",
        "itinerary_activity_title",
        "itinerary_activity_id",
        "itinerary_day_plan_id",
        "event_type",
        "preferred_day_number",
        "saved_at",
        "start_date",
        "end_date",
        "start_time",
        "end_time",
        "itinerary_activity_start_time",
        "itinerary_activity_end_time",
        "guest_note",
        "preferred_day_plan_id",
        "preferred_day_title",
        "host_status",
        "host_action_at",
        "host_note",
    }
)

_GUEST_SAVED_EVENT_LIST_KEYS = frozenset({"cities", "regions"})

_HOST_SAVED_EVENT_READ_KEYS = _GUEST_SAVED_EVENT_KEYS

_GUEST_SAVED_EVENT_READ_KEYS = _GUEST_SAVED_EVENT_KEYS - {
    "itinerary_activity_id",
    "itinerary_day_plan_id",
    "host_status",
    "host_action_at",
    "host_note",
}


def _sanitize_saved_event_row(row: Dict[str, Any], *, for_host: bool = False) -> Dict[str, Any]:
    from app.services.host_offerings_for_guest import scrub_contact_from_text, _scrub_safe_value

    allowed_keys = _HOST_SAVED_EVENT_READ_KEYS if for_host else _GUEST_SAVED_EVENT_READ_KEYS
    safe: Dict[str, Any] = {}
    for k, v in row.items():
        if k not in allowed_keys:
            continue
        if k in _GUEST_SAVED_EVENT_LIST_KEYS and v is not None:
            safe[k] = _scrub_safe_value(v)
        elif k in _GUEST_SAVED_EVENT_TEXT_KEYS and v is not None:
            safe[k] = scrub_contact_from_text(
                str(v), scrub_urls=k in {"url", "description"}
            )
        elif k == "booking_required" and isinstance(v, str):
            safe[k] = scrub_contact_from_text(v)
        else:
            safe[k] = v
    if not for_host:
        safe["in_itinerary"] = bool(
            row.get("itinerary_activity_id") or row.get("itinerary_activity_title")
        )
    return safe


def _filter_saved_event_write(payload: Dict[str, Any], *, for_host: bool = False) -> Dict[str, Any]:
    allowed = _HOST_SAVED_EVENT_PATCH_KEYS if for_host else _GUEST_SAVED_EVENT_WRITE_KEYS
    return {k: v for k, v in payload.items() if k in allowed}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_store(raw: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    block = raw.get(SAVED_EVENTS_KEY)
    if not isinstance(block, dict):
        return {}
    by_id = block.get("by_id")
    return dict(by_id) if isinstance(by_id, dict) else {}


def _merge_seasonal(existing: Any, by_id: Dict[str, Dict[str, Any]]) -> dict:
    base = dict(existing) if isinstance(existing, dict) else {}
    base[SAVED_EVENTS_KEY] = {
        "by_id": by_id,
        "updated_at": _now_iso(),
    }
    return base


def _guest_visible(row: Dict[str, Any]) -> bool:
    title = str(row.get("title") or "")
    blob = f"{title} {row.get('description') or ''}".lower()
    return not any(p in blob for p in NON_GUEST_SAVED_PATTERNS)


class GuestSavedEventsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_group(self, group_id: uuid.UUID) -> Optional[GuestGroup]:
        result = await self.db.execute(select(GuestGroup).where(GuestGroup.id == group_id))
        return result.scalar_one_or_none()

    async def list_for_group(
        self, group_id: uuid.UUID, *, for_host: bool = False
    ) -> Dict[str, Any]:
        group = await self._get_group(group_id)
        if not group:
            return {"saved_event_ids": [], "saved_events": []}
        by_id = _load_store(group.seasonal_preferences)
        rows = [
            _sanitize_saved_event_row(v, for_host=for_host)
            for v in by_id.values()
            if isinstance(v, dict) and _guest_visible(v)
        ]
        rows.sort(key=lambda r: r.get("saved_at") or "", reverse=True)
        ids = [str(r.get("event_id")) for r in rows if r.get("event_id")]
        return {"saved_event_ids": ids, "saved_events": rows}

    async def upsert(
        self,
        group_id: uuid.UUID,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        group = await self._get_group(group_id)
        if not group:
            raise ValueError("Guest group not found")
        event_id = str(payload.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("event_id is required")

        by_id = _load_store(group.seasonal_preferences)
        existing = by_id.get(event_id, {}) if isinstance(by_id.get(event_id), dict) else {}
        filtered = _filter_saved_event_write(payload)
        row = {**existing, **{k: v for k, v in filtered.items() if v is not None}}
        row["event_id"] = event_id
        row.setdefault("saved_at", _now_iso())
        by_id[event_id] = row

        await self.db.execute(
            update(GuestGroup)
            .where(GuestGroup.id == group_id)
            .values(seasonal_preferences=_merge_seasonal(group.seasonal_preferences, by_id))
        )
        await self.db.commit()
        return await self.list_for_group(group_id)

    async def patch(
        self,
        group_id: uuid.UUID,
        event_id: str,
        patch: Dict[str, Any],
        *,
        for_host: bool = False,
    ) -> Dict[str, Any]:
        group = await self._get_group(group_id)
        if not group:
            raise ValueError("Guest group not found")
        by_id = _load_store(group.seasonal_preferences)
        if event_id not in by_id:
            raise KeyError(event_id)
        row = dict(by_id[event_id])
        filtered = _filter_saved_event_write(patch, for_host=for_host)
        row.update({k: v for k, v in filtered.items() if v is not None})
        if not for_host and "guest_action" in filtered:
            row["guest_action_at"] = _now_iso()
        row["event_id"] = event_id
        by_id[event_id] = row
        await self.db.execute(
            update(GuestGroup)
            .where(GuestGroup.id == group_id)
            .values(seasonal_preferences=_merge_seasonal(group.seasonal_preferences, by_id))
        )
        await self.db.commit()
        return await self.list_for_group(group_id, for_host=for_host)

    async def remove(self, group_id: uuid.UUID, event_id: str) -> Dict[str, Any]:
        group = await self._get_group(group_id)
        if not group:
            raise ValueError("Guest group not found")
        by_id = _load_store(group.seasonal_preferences)
        by_id.pop(event_id, None)
        await self.db.execute(
            update(GuestGroup)
            .where(GuestGroup.id == group_id)
            .values(seasonal_preferences=_merge_seasonal(group.seasonal_preferences, by_id))
        )
        await self.db.commit()
        return await self.list_for_group(group_id)

    async def convert_to_itinerary_activity(
        self,
        group_id: uuid.UUID,
        event_id: str,
        host_id: uuid.UUID,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or reuse an itinerary activity from a guest-saved event."""
        from datetime import datetime, time as time_type, timedelta

        from sqlalchemy import select

        from app.models.itinerary import ActivityCreate, ActivityResponse, DayPlan, Itinerary, ItineraryActivity
        from app.services.itinerary_service import ItineraryService

        group = await self._get_group(group_id)
        if not group:
            raise ValueError("Guest group not found")

        by_id = _load_store(group.seasonal_preferences)
        row = by_id.get(event_id)
        if not isinstance(row, dict):
            raise KeyError(event_id)

        existing_activity_id = row.get("itinerary_activity_id")
        day_plan_id_raw = body.get("day_plan_id")
        if not day_plan_id_raw:
            raise ValueError("day_plan_id is required")
        day_plan_id = uuid.UUID(str(day_plan_id_raw))

        day_result = await self.db.execute(select(DayPlan).where(DayPlan.id == day_plan_id))
        day_plan = day_result.scalar_one_or_none()
        if not day_plan:
            raise ValueError("Day plan not found")

        itin_result = await self.db.execute(
            select(Itinerary).where(Itinerary.id == day_plan.itinerary_id)
        )
        itinerary = itin_result.scalar_one_or_none()
        if not itinerary or itinerary.host_id != host_id:
            raise ValueError("Itinerary not found for host")

        if existing_activity_id:
            act_result = await self.db.execute(
                select(ItineraryActivity).where(
                    ItineraryActivity.id == uuid.UUID(str(existing_activity_id))
                )
            )
            activity_row = act_result.scalar_one_or_none()
            activity_dict = (
                ActivityResponse.model_validate(activity_row).model_dump()
                if activity_row
                else {"id": existing_activity_id}
            )
            listing = await self.list_for_group(group_id, for_host=True)
            return {**listing, "activity": activity_dict, "already_added": True}

        start_raw = str(body.get("scheduled_start_time") or "19:00")
        parts = start_raw.split(":")
        hour = int(parts[0]) if parts else 19
        minute = int(parts[1]) if len(parts) > 1 else 0
        duration = int(body.get("estimated_duration") or 120)
        start_dt = datetime.combine(day_plan.date, time_type(hour, minute))
        end_dt = start_dt + timedelta(minutes=duration)

        cities = row.get("cities") or []
        location_name = cities[0] if cities else "Event location"
        activity_data = ActivityCreate(
            title=str(row.get("title") or "Saved event"),
            description=str(row.get("description") or row.get("plan_hint") or ""),
            activity_type="event",
            category="events",
            location_name=location_name,
            scheduled_start_time=start_dt,
            scheduled_end_time=end_dt,
            estimated_duration=duration,
            address=location_name,
            booking_required=bool(row.get("booking_required")),
        )
        itinerary_service = ItineraryService(self.db)
        created = await itinerary_service.add_activity_to_day(day_plan_id, activity_data)
        if not created:
            raise ValueError("Could not create itinerary activity")

        row["itinerary_activity_id"] = str(created.id)
        row["itinerary_day_plan_id"] = str(day_plan_id)
        row["itinerary_activity_title"] = created.title
        row["itinerary_activity_start_time"] = start_dt.isoformat()
        row["itinerary_activity_end_time"] = end_dt.isoformat()
        row["host_status"] = row.get("host_status") or "planned"
        row["host_action_at"] = _now_iso()
        by_id[event_id] = row

        await self.db.execute(
            update(GuestGroup)
            .where(GuestGroup.id == group_id)
            .values(seasonal_preferences=_merge_seasonal(group.seasonal_preferences, by_id))
        )
        await self.db.commit()
        listing = await self.list_for_group(group_id, for_host=True)
        return {**listing, "activity": created.model_dump(), "already_added": False}
