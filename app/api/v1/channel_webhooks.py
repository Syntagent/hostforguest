"""
Inbound webhooks from Booking.com (or proxy). Verifies HMAC when secret is configured.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_webhook_hmac_secret
from app.core.config import settings
from app.core.database import get_db
from app.models.channel_integration import ChannelType
from app.services.channel_integration_service import ChannelIntegrationService
from app.services.channel_sync_service import ChannelSyncService
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/booking-com")
async def booking_com_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Channel-Signature") or request.headers.get("X-Booking-Signature") or ""
    secret = (settings.channel_webhook_secret or "").strip()
    require_webhook_hmac_secret(secret, "Channel")
    if secret and not _verify_signature(body, sig, secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    try:
        data: Dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON")

    hotel_id = str(data.get("hotel_id") or data.get("property_id") or "").strip()
    if not hotel_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "hotel_id required")

    rls = RLSService(db)
    async with rls.worker_bypass():
        integ = ChannelIntegrationService(db)
        acc = await integ.get_account_by_hotel_id(hotel_id, ChannelType.BOOKING_COM.value)
        if not acc:
            logger.warning("Webhook for unknown hotel_id=%s", hotel_id)
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown property")

        reservations: List[Dict[str, Any]] = []
        if "reservations" in data:
            reservations = data["reservations"]
        elif "reservation" in data:
            reservations = [data["reservation"]]
        else:
            reservations = [data]

        sync = ChannelSyncService(db)
        processed = 0
        errors: List[str] = []
        from app.integrations.booking_com import mappers

        for raw in reservations:
            try:
                norm = mappers.normalized_reservation_from_dict(raw)
                norm.setdefault("external_hotel_id", hotel_id)
                if await sync.ingest_inbound_reservation(acc, norm):
                    processed += 1
            except Exception as e:
                logger.exception("Webhook ingest error: %s", e)
                errors.append(str(e))

    return {"ok": True, "processed": processed, "errors": errors}
