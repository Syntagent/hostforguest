"""
Host-facing API for Booking.com channel connect, mapping, sync, and health.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.hosts import get_current_host
from app.core.database import get_db
from app.models.channel_integration import ChannelAccount
from app.models.host import Host
from app.services.channel_integration_service import ChannelIntegrationService
from app.services.channel_sync_service import ChannelSyncService

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectBookingComRequest(BaseModel):
    hotel_id: str = Field(..., min_length=1, max_length=64)
    api_username: str = Field(..., min_length=1)
    api_password: str = Field(..., min_length=1)


class ChannelAccountResponse(BaseModel):
    id: str
    channel: str
    status: str
    external_hotel_id: Optional[str]
    feature_enabled: bool

    class Config:
        from_attributes = True


class MappingCreateRequest(BaseModel):
    local_entity_type: str = Field(..., pattern="^(host|partner)$")
    local_entity_id: str
    external_room_id: str = Field(..., min_length=1)
    external_rate_id: Optional[str] = None


class MappingResponse(BaseModel):
    id: str
    local_entity_type: str
    local_entity_id: str
    external_room_id: Optional[str]
    external_rate_id: Optional[str]
    active: bool

    class Config:
        from_attributes = True


class PushAvailabilityRequest(BaseModel):
    mapping_id: str
    date_from: str
    date_to: str
    available: int = Field(ge=0, le=999)


class PushRatesRequest(BaseModel):
    mapping_id: str
    date_from: str
    date_to: str
    price: float = Field(gt=0)
    currency: str = "EUR"


class ChannelStatusResponse(BaseModel):
    account: Optional[ChannelAccountResponse] = None


class SyncHealthResponse(BaseModel):
    account_id: str
    reservations_cursor: Optional[str]
    last_reservations_poll_at: Optional[str]
    last_availability_push_at: Optional[str]
    last_rates_push_at: Optional[str]
    last_full_sync_at: Optional[str]
    last_error: Optional[str]
    consecutive_errors: int


def _to_account_resp(acc: ChannelAccount) -> ChannelAccountResponse:
    return ChannelAccountResponse(
        id=str(acc.id),
        channel=acc.channel,
        status=acc.status,
        external_hotel_id=acc.external_hotel_id,
        feature_enabled=bool(acc.feature_enabled),
    )


@router.post("/booking-com/connect", response_model=ChannelAccountResponse)
async def connect_booking_com(
    body: ConnectBookingComRequest,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    svc = ChannelIntegrationService(db)
    acc = await svc.connect_booking_com(
        host.id,
        body.hotel_id.strip(),
        body.api_username.strip(),
        body.api_password,
    )
    return _to_account_resp(acc)


@router.delete("/booking-com/disconnect")
async def disconnect_booking_com(
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    svc = ChannelIntegrationService(db)
    disconnected = await svc.disconnect(host.id)
    return {"ok": True, "disconnected": disconnected}


@router.get("/status", response_model=ChannelStatusResponse)
async def channel_status(
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    svc = ChannelIntegrationService(db)
    acc = await svc.get_account_for_host(host.id)
    return ChannelStatusResponse(account=_to_account_resp(acc) if acc else None)


@router.post("/{account_id}/mappings", response_model=MappingResponse)
async def create_mapping(
    account_id: uuid.UUID,
    body: MappingCreateRequest,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    svc = ChannelIntegrationService(db)
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    try:
        m = await svc.add_mapping(
            account_id,
            host.id,
            body.local_entity_type,
            uuid.UUID(body.local_entity_id),
            body.external_room_id.strip(),
            body.external_rate_id.strip() if body.external_rate_id else None,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return MappingResponse(
        id=str(m.id),
        local_entity_type=m.local_entity_type,
        local_entity_id=str(m.local_entity_id),
        external_room_id=m.external_room_id,
        external_rate_id=m.external_rate_id,
        active=bool(m.active),
    )


@router.get("/{account_id}/mappings", response_model=List[MappingResponse])
async def list_mappings(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    svc = ChannelIntegrationService(db)
    rows = await svc.list_mappings(account_id, host.id)
    return [
        MappingResponse(
            id=str(m.id),
            local_entity_type=m.local_entity_type,
            local_entity_id=str(m.local_entity_id),
            external_room_id=m.external_room_id,
            external_rate_id=m.external_rate_id,
            active=bool(m.active),
        )
        for m in rows
    ]


@router.post("/{account_id}/sync/full")
async def sync_full(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    sync = ChannelSyncService(db)
    return await sync.full_sync(account_id)


@router.post("/{account_id}/sync/reservations")
async def sync_reservations(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    sync = ChannelSyncService(db)
    return await sync.poll_reservations(account_id)


@router.post("/{account_id}/push/availability")
async def push_availability(
    account_id: uuid.UUID,
    body: PushAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    sync = ChannelSyncService(db)
    ok = await sync.push_availability_for_mapping(
        account_id,
        uuid.UUID(body.mapping_id),
        body.date_from,
        body.date_to,
        body.available,
    )
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Availability push failed")
    return {"ok": True}


@router.post("/{account_id}/push/rates")
async def push_rates(
    account_id: uuid.UUID,
    body: PushRatesRequest,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    sync = ChannelSyncService(db)
    ok = await sync.push_rates_for_mapping(
        account_id,
        uuid.UUID(body.mapping_id),
        body.date_from,
        body.date_to,
        body.price,
        body.currency,
    )
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Rates push failed")
    return {"ok": True}


@router.get("/{account_id}/health", response_model=SyncHealthResponse)
async def sync_health(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    acc = await db.get(ChannelAccount, account_id)
    if not acc or acc.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel account not found")
    integ = ChannelIntegrationService(db)
    st = await integ.get_sync_state(account_id)

    def _iso(dt):
        return dt.isoformat() if dt else None

    return SyncHealthResponse(
        account_id=str(account_id),
        reservations_cursor=st.reservations_cursor,
        last_reservations_poll_at=_iso(st.last_reservations_poll_at),
        last_availability_push_at=_iso(st.last_availability_push_at),
        last_rates_push_at=_iso(st.last_rates_push_at),
        last_full_sync_at=_iso(st.last_full_sync_at),
        last_error=st.last_error,
        consecutive_errors=int(st.consecutive_errors or 0),
    )


@router.post("/events/{event_id}/replay")
async def replay_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    sync = ChannelSyncService(db)
    return await sync.replay_event_log(event_id, host.id)


class OtaOverrideBody(BaseModel):
    local_sync_override: bool


@router.patch("/bookings/{booking_id}/ota-override")
async def set_booking_ota_override(
    booking_id: uuid.UUID,
    body: OtaOverrideBody,
    db: AsyncSession = Depends(get_db),
    host: Host = Depends(get_current_host),
):
    from app.models.partner import PartnerBooking

    b = await db.get(PartnerBooking, booking_id)
    if not b or b.host_id != host.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    b.local_sync_override = body.local_sync_override
    await db.commit()
    return {"ok": True, "booking_id": str(booking_id), "local_sync_override": b.local_sync_override}
