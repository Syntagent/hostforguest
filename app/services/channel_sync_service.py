"""
Two-way sync: pull reservations from Booking.com, push availability/rates.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.booking_com import mappers
from app.models.channel_integration import (
    ChannelAccount,
    ChannelAccountStatus,
    ChannelEventStatus,
    ChannelType,
)
from app.models.partner import BookingStatus, PartnerBooking
from app.services.channel_conflict_service import ChannelConflictService, _coerce_dt
from app.services.channel_integration_service import ChannelIntegrationService
from app.utils.json_safe import json_safe_dict

logger = logging.getLogger(__name__)


def _map_ota_status(raw: str) -> str:
    s = (raw or "").lower()
    if s in ("cancelled", "canceled"):
        return BookingStatus.CANCELLED.value
    if s in ("confirmed", "ok", "booked"):
        return BookingStatus.CONFIRMED.value
    return BookingStatus.PENDING.value


class ChannelSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration = ChannelIntegrationService(db)
        self.conflict = ChannelConflictService()

    async def poll_reservations(self, account_id: uuid.UUID) -> Dict[str, Any]:
        acc = await self.db.get(ChannelAccount, account_id)
        if not acc or acc.status != ChannelAccountStatus.CONNECTED.value:
            return {"ok": False, "error": "account not connected"}
        if not acc.external_hotel_id:
            return {"ok": False, "error": "missing external_hotel_id"}
        st = await self.integration.get_sync_state(account_id)
        client = self.integration.build_client(acc)
        rows, next_cursor = await client.fetch_reservations(
            acc.external_hotel_id, st.reservations_cursor
        )
        processed = 0
        errors: List[str] = []
        for norm in rows:
            try:
                if await self._ingest_reservation(acc, norm):
                    processed += 1
            except Exception as e:
                logger.exception("Ingest reservation failed: %s", e)
                errors.append(str(e))
                try:
                    await self.db.rollback()
                except Exception:
                    pass
        st.reservations_cursor = next_cursor or st.reservations_cursor
        st.last_reservations_poll_at = datetime.utcnow()
        st.consecutive_errors = len(errors)
        st.last_error = errors[0] if errors else None
        await self.db.commit()
        return {"ok": True, "fetched": len(rows), "processed": processed, "errors": errors}

    async def _apply_reservation_norm(self, acc: ChannelAccount, norm: Dict[str, Any]) -> str:
        """
        Upsert PartnerBooking from normalized payload.
        Returns outcome: applied | skipped_override
        """
        ext_id = norm.get("external_reservation_id")
        if not ext_id:
            return "noop"
        ext_ts = _coerce_dt(norm.get("external_updated_at"))
        if ext_ts is None:
            ext_ts = datetime.utcnow()

        stmt = select(PartnerBooking).where(
            and_(
                PartnerBooking.source_channel == ChannelType.BOOKING_COM.value,
                PartnerBooking.external_reservation_id == ext_id,
            )
        )
        r = await self.db.execute(stmt)
        existing = r.scalar_one_or_none()

        status_val = _map_ota_status(norm.get("status", ""))
        amount = float(norm.get("total_price") or 0)
        room_id = norm.get("external_room_id")

        if existing:
            if not self.conflict.accept_inbound_update(existing, norm.get("external_updated_at")):
                return "skipped_override"
            existing.external_status = norm.get("status")
            existing.external_updated_at = ext_ts
            existing.status = status_val
            existing.booking_amount = amount
            existing.external_room_id = room_id
            existing.booking_details = json_safe_dict(
                {**(existing.booking_details or {}), "channel": norm.get("raw", norm)}
            )
            if status_val == BookingStatus.CANCELLED.value:
                existing.cancelled_at = datetime.utcnow()
        else:
            pb = PartnerBooking(
                id=uuid.uuid4(),
                host_id=acc.host_id,
                guest_group_id=None,
                partner_id=None,
                attraction_id=None,
                booking_reference=f"BC-{ext_id}",
                booking_date=datetime.utcnow(),
                service_date=None,
                booking_amount=amount,
                currency=norm.get("currency") or "EUR",
                commission_rate=0.0,
                commission_amount=0.0,
                status=status_val,
                source_channel=ChannelType.BOOKING_COM.value,
                external_reservation_id=ext_id,
                external_room_id=room_id,
                external_status=norm.get("status"),
                external_updated_at=ext_ts,
                booking_details=json_safe_dict({"channel_payload": norm.get("raw", norm)}),
            )
            self.db.add(pb)
        await self.db.commit()
        return "applied"

    async def _ingest_reservation(self, acc: ChannelAccount, norm: Dict[str, Any]) -> bool:
        """Returns True if this row was handled (including skipped override)."""
        ext_id = norm.get("external_reservation_id")
        if not ext_id:
            return False
        ext_ts = _coerce_dt(norm.get("external_updated_at"))
        if ext_ts is None:
            ext_ts = datetime.utcnow()
        idem = f"booking_com:{ext_id}:{ext_ts.isoformat()}"
        log, new_event = await self.integration.record_event(
            acc.id,
            idem,
            "reservation_upsert",
            "inbound",
            norm,
        )
        if not new_event:
            return False

        try:
            outcome = await self._apply_reservation_norm(acc, norm)
        except Exception as e:
            logger.exception("Apply reservation failed for %s", ext_id)
            await self.integration.mark_event(log.id, ChannelEventStatus.FAILED.value, str(e))
            return True

        if outcome == "skipped_override":
            await self.integration.mark_event(
                log.id, ChannelEventStatus.PROCESSED.value, "skipped_local_override"
            )
        else:
            await self.integration.mark_event(log.id, ChannelEventStatus.PROCESSED.value, None)
        return True

    async def replay_event_log(self, event_log_id: uuid.UUID, host_id: uuid.UUID) -> Dict[str, Any]:
        """Re-process a failed inbound event (new idempotency key)."""
        from app.models.channel_integration import ChannelEventLog

        log = await self.db.get(ChannelEventLog, event_log_id)
        if not log:
            return {"ok": False, "error": "not_found"}
        acc = await self.db.get(ChannelAccount, log.channel_account_id)
        if not acc or acc.host_id != host_id:
            return {"ok": False, "error": "forbidden"}
        log.idempotency_key = f"{log.idempotency_key}:replay:{uuid.uuid4()}"
        log.status = ChannelEventStatus.PENDING.value
        log.error_message = None
        await self.db.commit()
        norm = log.payload or {}
        if log.event_type != "reservation_upsert":
            return {"ok": False, "error": "unsupported_event_type"}
        try:
            outcome = await self._apply_reservation_norm(acc, norm)
            if outcome == "skipped_override":
                await self.integration.mark_event(
                    log.id, ChannelEventStatus.PROCESSED.value, "skipped_local_override"
                )
            else:
                await self.integration.mark_event(log.id, ChannelEventStatus.PROCESSED.value, None)
            return {"ok": True, "outcome": outcome}
        except Exception as e:
            await self.integration.mark_event(log.id, ChannelEventStatus.FAILED.value, str(e))
            return {"ok": False, "error": str(e)}

    async def push_availability_for_mapping(
        self,
        account_id: uuid.UUID,
        mapping_id: uuid.UUID,
        date_from: str,
        date_to: str,
        available: int,
    ) -> bool:
        acc = await self.db.get(ChannelAccount, account_id)
        if not acc or not acc.external_hotel_id:
            return False
        from app.models.channel_integration import ChannelPropertyMapping

        m = await self.db.get(ChannelPropertyMapping, mapping_id)
        if not m or m.channel_account_id != account_id or not m.external_room_id:
            return False
        client = self.integration.build_client(acc)
        payload = mappers.build_availability_update_payload(
            acc.external_hotel_id, m.external_room_id, date_from, date_to, available
        )
        ok = await client.push_availability(payload)
        st = await self.integration.get_sync_state(account_id)
        st.last_availability_push_at = datetime.utcnow()
        if not ok:
            st.consecutive_errors = (st.consecutive_errors or 0) + 1
            st.last_error = "availability push failed"
        await self.db.commit()
        return ok

    async def push_rates_for_mapping(
        self,
        account_id: uuid.UUID,
        mapping_id: uuid.UUID,
        date_from: str,
        date_to: str,
        price: float,
        currency: str = "EUR",
    ) -> bool:
        acc = await self.db.get(ChannelAccount, account_id)
        if not acc or not acc.external_hotel_id:
            return False
        from app.models.channel_integration import ChannelPropertyMapping

        m = await self.db.get(ChannelPropertyMapping, mapping_id)
        if not m or m.channel_account_id != account_id or not m.external_room_id:
            return False
        client = self.integration.build_client(acc)
        payload = mappers.build_rate_update_payload(
            acc.external_hotel_id,
            m.external_room_id,
            m.external_rate_id,
            date_from,
            date_to,
            price,
            currency,
        )
        ok = await client.push_rates(payload)
        st = await self.integration.get_sync_state(account_id)
        st.last_rates_push_at = datetime.utcnow()
        if not ok:
            st.consecutive_errors = (st.consecutive_errors or 0) + 1
            st.last_error = "rates push failed"
        await self.db.commit()
        return ok

    async def full_sync(self, account_id: uuid.UUID) -> Dict[str, Any]:
        res = await self.poll_reservations(account_id)
        st = await self.integration.get_sync_state(account_id)
        st.last_full_sync_at = datetime.utcnow()
        await self.db.commit()
        res["last_full_sync_at"] = st.last_full_sync_at.isoformat()
        return res

    async def ingest_inbound_reservation(self, acc: ChannelAccount, norm: Dict[str, Any]) -> bool:
        """Public entry for webhooks / external callers."""
        return await self._ingest_reservation(acc, norm)
