"""Telegram self-service pairing — web codes and bot /link command."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host, HostProfile
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)

_PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PAIRING_CODE_LEN = 6
_PAIRING_TTL_MINUTES = 10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_pairing_code() -> str:
    """6-char uppercase alphanumeric code (no O/0/I/1)."""
    return "".join(secrets.choice(_PAIRING_ALPHABET) for _ in range(_PAIRING_CODE_LEN))


def _expires_in_seconds(expires_at: Optional[datetime]) -> Optional[int]:
    if not expires_at:
        return None
    delta = (expires_at - _utcnow()).total_seconds()
    return max(0, int(delta))


class TelegramPairingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_pairing_code(self, host_id: uuid.UUID) -> Dict[str, Any]:
        """Return active pairing code for host, or generate a new one."""
        host = await self._get_host(host_id)
        if not host:
            raise ValueError("Host not found")

        if host.telegram_id is not None:
            return self._linked_payload(host)

        now = _utcnow()
        if (
            host.telegram_pairing_code
            and host.telegram_pairing_expires
            and host.telegram_pairing_expires > now
        ):
            return self._code_payload(host)

        code = await self._unique_code()
        expires_at = now + timedelta(minutes=_PAIRING_TTL_MINUTES)
        host.telegram_pairing_code = code
        host.telegram_pairing_expires = expires_at
        await self.db.commit()
        await self.db.refresh(host)
        return self._code_payload(host)

    async def unlink_telegram(self, host_id: uuid.UUID) -> bool:
        host = await self._get_host(host_id)
        if not host:
            return False
        host.telegram_id = None
        host.telegram_linked_at = None
        host.telegram_pairing_code = None
        host.telegram_pairing_expires = None
        await self.db.commit()
        return True

    async def link_by_code(self, telegram_id: int, code: str) -> Dict[str, Any]:
        """
        Link telegram user to host via pairing code.

        Returns dict with keys: ok, response, host_id (optional), already_linked (optional).
        """
        normalized = (code or "").strip().upper()
        if len(normalized) != _PAIRING_CODE_LEN:
            return {
                "ok": False,
                "response": "Kod nije valjan ili je istekao. Idite na web za novi kod.",
            }

        async with RLSService(self.db).worker_bypass():
            existing_stmt = select(Host).where(Host.telegram_id == telegram_id)
            existing_result = await self.db.execute(existing_stmt)
            existing_host = existing_result.scalar_one_or_none()
            if existing_host:
                name = f"{existing_host.first_name} {existing_host.last_name}".strip()
                return {
                    "ok": False,
                    "already_linked": True,
                    "host_id": existing_host.id,
                    "response": f"Već ste povezani s računom {name}",
                }

            now = _utcnow()
            stmt = select(Host).where(
                and_(
                    Host.telegram_pairing_code == normalized,
                    Host.telegram_pairing_expires.is_not(None),
                    Host.telegram_pairing_expires > now,
                )
            )
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()
            if not host:
                return {
                    "ok": False,
                    "response": "Kod nije valjan ili je istekao. Idite na web za novi kod.",
                }

            host.telegram_id = telegram_id
            host.telegram_linked_at = now
            host.telegram_pairing_code = None
            host.telegram_pairing_expires = None
            await self.db.commit()

            profile_stmt = select(HostProfile).where(HostProfile.host_id == host.id)
            profile_result = await self.db.execute(profile_stmt)
            profile = profile_result.scalar_one_or_none()
            name = f"{host.first_name} {host.last_name}".strip()
            property_name = None
            if profile and profile.property_name:
                property_name = profile.property_name
            elif host.business_name:
                property_name = host.business_name

            welcome = f"✅ Povezano! Dobrodošao, {name}!"
            if property_name:
                welcome += f"\n\n🏠 {property_name}"

            return {
                "ok": True,
                "host_id": host.id,
                "response": welcome,
            }

    async def _get_host(self, host_id: uuid.UUID) -> Optional[Host]:
        stmt = select(Host).where(Host.id == host_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _unique_code(self, attempts: int = 8) -> str:
        for _ in range(attempts):
            code = generate_pairing_code()
            stmt = select(Host.id).where(Host.telegram_pairing_code == code).limit(1)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                return code
        raise RuntimeError("Could not generate unique telegram pairing code")

    def _code_payload(self, host: Host) -> Dict[str, Any]:
        return {
            "linked": False,
            "code": host.telegram_pairing_code,
            "expires_at": host.telegram_pairing_expires,
            "expires_in_seconds": _expires_in_seconds(host.telegram_pairing_expires),
            "linked_at": None,
            "telegram_id": None,
        }

    def _linked_payload(self, host: Host) -> Dict[str, Any]:
        return {
            "linked": True,
            "code": None,
            "expires_at": None,
            "expires_in_seconds": None,
            "linked_at": host.telegram_linked_at,
            "telegram_id": host.telegram_id,
        }
