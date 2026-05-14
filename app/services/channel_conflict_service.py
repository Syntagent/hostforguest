"""
Deterministic rules for applying inbound OTA updates vs local state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from app.models.partner import PartnerBooking


def _coerce_dt(value: Union[str, datetime, None]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


class ChannelConflictService:
    """When to accept an inbound change from a channel."""

    @staticmethod
    def accept_inbound_update(
        booking: PartnerBooking,
        new_external_updated_at: Optional[Union[str, datetime]],
    ) -> bool:
        if getattr(booking, "local_sync_override", False):
            return False
        new_dt = _coerce_dt(new_external_updated_at)
        if new_dt is None:
            return True
        current = getattr(booking, "external_updated_at", None)
        if current is None:
            return True
        return new_dt >= current
