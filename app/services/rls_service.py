"""
Row-Level Security (RLS) service for PostgreSQL.

**Status (Phase 2):** Wired into host auth dependencies and bypass contexts for
login, guest access, and worker jobs. Policies live in
``migrations/enable_row_level_security_policies.sql`` and
``migrations/rls_phase2_nobypassrls_roles_and_bypass_policies.sql`` and
``migrations/rls_phase3_extend_host_scoped_tables.sql`` and
``migrations/rls_phase5_content_pipeline_and_contributions.sql``.

Runtime should connect as ``tourist_guide_app`` (``POSTGRES_APP_USER``) so RLS
is enforced; migrations use the owner role (``POSTGRES_USER``).

See ``docs/TENANT_ISOLATION_AUDIT.md`` and ``docs/TENANT_ISOLATION_CONTRACT.md``.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_BYPASS_KEYS = (
    "app.rls_bypass",
    "app.login_email",
    "app.guest_access_code",
    "app.guest_group_id",
)


class RLSService:
    """
    Service for managing Row-Level Security tenant context.

    Sets ``app.current_host_id`` and optional bypass GUCs on the active session
    using transaction-local ``set_config`` (``is_local=true``).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _set_config(self, key: str, value: str) -> None:
        stmt = text("SELECT set_config(:key, :value, true)")
        await self.db.execute(stmt, {"key": key, "value": value})

    async def _current_bypass(self) -> str:
        stmt = text("SELECT current_setting(:key, true)")
        result = await self.db.execute(stmt, {"key": "app.rls_bypass"})
        value = result.scalar()
        return value or ""

    async def set_host_context(self, host_id: uuid.UUID) -> bool:
        """Set current host context for RLS on this transaction."""
        try:
            await self._set_config("app.current_host_id", str(host_id))
            logger.debug("Set RLS context for host %s", host_id)
            return True
        except Exception as e:
            logger.error("Error setting RLS context: %s", e)
            return False

    async def clear_host_context(self) -> bool:
        """Clear current host context for this transaction."""
        try:
            await self._set_config("app.current_host_id", "")
            return True
        except Exception as e:
            logger.error("Error clearing RLS context: %s", e)
            return False

    async def set_bypass(
        self,
        mode: str,
        *,
        login_email: Optional[str] = None,
        guest_access_code: Optional[str] = None,
        guest_group_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Set transaction-local bypass mode and optional supporting GUCs."""
        try:
            await self._set_config("app.rls_bypass", mode)
            if login_email is not None:
                await self._set_config("app.login_email", login_email.strip().lower())
            if guest_access_code is not None:
                await self._set_config("app.guest_access_code", guest_access_code.strip().upper())
            if guest_group_id is not None:
                await self._set_config("app.guest_group_id", str(guest_group_id))
            return True
        except Exception as e:
            logger.error("Error setting RLS bypass %s: %s", mode, e)
            return False

    async def clear_bypass(self) -> bool:
        """Clear bypass GUCs for this transaction."""
        try:
            for key in _BYPASS_KEYS:
                await self._set_config(key, "")
            return True
        except Exception as e:
            logger.error("Error clearing RLS bypass: %s", e)
            return False

    @asynccontextmanager
    async def login_bypass(self, email: str) -> AsyncIterator[None]:
        """Allow email-based host lookup during authentication."""
        parent_bypass = await self._current_bypass()
        await self.set_bypass("login", login_email=email)
        try:
            yield
        finally:
            await self._set_config("app.login_email", "")
            await self._set_config("app.rls_bypass", parent_bypass)

    @asynccontextmanager
    async def register_bypass(self) -> AsyncIterator[None]:
        """Allow host registration INSERT before tenant context exists."""
        parent_bypass = await self._current_bypass()
        await self.set_bypass("register")
        try:
            yield
        finally:
            try:
                await self._set_config("app.rls_bypass", parent_bypass)
            except Exception:
                pass

    @asynccontextmanager
    async def session_bypass(self) -> AsyncIterator[None]:
        """Allow user_sessions access by token before host GUC is set."""
        parent_bypass = await self._current_bypass()
        await self.set_bypass("session")
        try:
            yield
        finally:
            try:
                await self._set_config("app.rls_bypass", parent_bypass)
            except Exception:
                pass

    @asynccontextmanager
    async def guest_bypass(
        self,
        access_code: str,
        *,
        guest_group_id: Optional[uuid.UUID] = None,
    ) -> AsyncIterator[None]:
        """Allow guest access-code flows without a host session."""
        parent_bypass = await self._current_bypass()
        await self.set_bypass(
            "guest",
            guest_access_code=access_code,
            guest_group_id=guest_group_id,
        )
        if guest_group_id is None:
            await self._set_config("app.guest_group_id", "")
        try:
            yield
        finally:
            try:
                await self._set_config("app.guest_access_code", "")
                await self._set_config("app.guest_group_id", "")
                await self._set_config("app.rls_bypass", parent_bypass)
            except Exception:
                pass

    @asynccontextmanager
    async def worker_bypass(self) -> AsyncIterator[None]:
        """Allow cross-tenant worker/cron jobs."""
        parent_bypass = await self._current_bypass()
        await self.set_bypass("worker")
        await self._set_config("app.current_host_id", "00000000-0000-0000-0000-000000000000")
        try:
            yield
        finally:
            try:
                await self._set_config("app.rls_bypass", parent_bypass)
                await self._set_config("app.current_host_id", "")
            except Exception:
                pass
