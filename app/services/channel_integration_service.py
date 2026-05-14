"""
CRUD and helpers for channel accounts, mappings, and sync state.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto_util import decrypt_secret, encrypt_secret
from app.utils.json_safe import json_safe_dict
from app.integrations.booking_com.client import BookingComClient
from app.models.channel_integration import (
    ChannelAccount,
    ChannelAccountStatus,
    ChannelEventLog,
    ChannelEventStatus,
    ChannelPropertyMapping,
    ChannelSyncState,
    ChannelType,
)

logger = logging.getLogger(__name__)


class ChannelIntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_for_host(
        self, host_id: uuid.UUID, channel: str = ChannelType.BOOKING_COM.value
    ) -> Optional[ChannelAccount]:
        stmt = select(ChannelAccount).where(
            ChannelAccount.host_id == host_id,
            ChannelAccount.channel == channel,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def connect_booking_com(
        self,
        host_id: uuid.UUID,
        hotel_id: str,
        api_username: str,
        api_password: str,
    ) -> ChannelAccount:
        existing = await self.get_account_for_host(host_id)
        if existing:
            existing.external_hotel_id = hotel_id
            existing.api_username_encrypted = encrypt_secret(api_username)
            existing.api_password_encrypted = encrypt_secret(api_password)
            existing.status = ChannelAccountStatus.CONNECTED.value
            existing.last_error = None
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        acc = ChannelAccount(
            id=uuid.uuid4(),
            host_id=host_id,
            channel=ChannelType.BOOKING_COM.value,
            status=ChannelAccountStatus.CONNECTED.value,
            external_hotel_id=hotel_id,
            api_username_encrypted=encrypt_secret(api_username),
            api_password_encrypted=encrypt_secret(api_password),
        )
        self.db.add(acc)
        await self.db.commit()
        await self.db.refresh(acc)
        await self._ensure_sync_state(acc.id)
        return acc

    async def disconnect(self, host_id: uuid.UUID) -> bool:
        acc = await self.get_account_for_host(host_id)
        if not acc:
            return False
        acc.status = ChannelAccountStatus.DISCONNECTED.value
        acc.api_username_encrypted = None
        acc.api_password_encrypted = None
        await self.db.commit()
        return True

    async def _ensure_sync_state(self, account_id: uuid.UUID) -> ChannelSyncState:
        stmt = select(ChannelSyncState).where(ChannelSyncState.channel_account_id == account_id)
        r = await self.db.execute(stmt)
        st = r.scalar_one_or_none()
        if st:
            return st
        st = ChannelSyncState(id=uuid.uuid4(), channel_account_id=account_id)
        self.db.add(st)
        await self.db.commit()
        await self.db.refresh(st)
        return st

    def build_client(self, account: ChannelAccount) -> BookingComClient:
        u = decrypt_secret(account.api_username_encrypted or "") or ""
        p = decrypt_secret(account.api_password_encrypted or "") or ""
        return BookingComClient(username=u, password=p)

    async def add_mapping(
        self,
        account_id: uuid.UUID,
        host_id: uuid.UUID,
        local_entity_type: str,
        local_entity_id: uuid.UUID,
        external_room_id: Optional[str],
        external_rate_id: Optional[str] = None,
    ) -> ChannelPropertyMapping:
        acc = await self.db.get(ChannelAccount, account_id)
        if not acc or acc.host_id != host_id:
            raise ValueError("Invalid channel account")
        m = ChannelPropertyMapping(
            id=uuid.uuid4(),
            channel_account_id=account_id,
            local_entity_type=local_entity_type,
            local_entity_id=local_entity_id,
            external_room_id=external_room_id,
            external_rate_id=external_rate_id,
        )
        self.db.add(m)
        await self.db.commit()
        await self.db.refresh(m)
        return m

    async def list_mappings(self, account_id: uuid.UUID, host_id: uuid.UUID) -> List[ChannelPropertyMapping]:
        acc = await self.db.get(ChannelAccount, account_id)
        if not acc or acc.host_id != host_id:
            return []
        stmt = select(ChannelPropertyMapping).where(
            ChannelPropertyMapping.channel_account_id == account_id
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def record_event(
        self,
        account_id: uuid.UUID,
        idempotency_key: str,
        event_type: str,
        direction: str,
        payload: dict,
    ) -> Tuple[ChannelEventLog, bool]:
        """
        Insert idempotent event. Returns (log, created_new).
        """
        stmt = select(ChannelEventLog).where(ChannelEventLog.idempotency_key == idempotency_key)
        r = await self.db.execute(stmt)
        existing = r.scalar_one_or_none()
        if existing:
            return existing, False
        log = ChannelEventLog(
            id=uuid.uuid4(),
            channel_account_id=account_id,
            idempotency_key=idempotency_key,
            event_type=event_type,
            direction=direction,
            payload=json_safe_dict(payload),
            status=ChannelEventStatus.PENDING.value,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log, True

    async def mark_event(
        self,
        log_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        log = await self.db.get(ChannelEventLog, log_id)
        if not log:
            return
        log.status = status
        log.error_message = error_message
        log.processed_at = datetime.utcnow()
        await self.db.commit()

    async def get_sync_state(self, account_id: uuid.UUID) -> ChannelSyncState:
        return await self._ensure_sync_state(account_id)

    async def list_connected_accounts(self) -> List[ChannelAccount]:
        stmt = select(ChannelAccount).where(
            ChannelAccount.status == ChannelAccountStatus.CONNECTED.value,
            ChannelAccount.feature_enabled == True,  # noqa: E712
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def get_account_by_hotel_id(
        self, hotel_id: str, channel: str = ChannelType.BOOKING_COM.value
    ) -> Optional[ChannelAccount]:
        stmt = select(ChannelAccount).where(
            ChannelAccount.external_hotel_id == hotel_id,
            ChannelAccount.channel == channel,
            ChannelAccount.status == ChannelAccountStatus.CONNECTED.value,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()
