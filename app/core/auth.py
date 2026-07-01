"""
Shared authentication dependencies for FastAPI endpoints.
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.host import Host
from app.services.host_service import HostService
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)


def allow_unconfigured_webhook_secret() -> bool:
    """Development and pytest may omit webhook secrets; production must not."""
    if settings.is_development:
        return True
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TOURISTGUIDE_PYTEST"))


def require_webhook_hmac_secret(configured_secret: str, service_label: str) -> None:
    """Reject webhook calls when the HMAC secret is unset outside dev/pytest."""
    if (configured_secret or "").strip():
        return
    if not allow_unconfigured_webhook_secret():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_label} webhook secret not configured",
        )


async def apply_host_rls_context(db: AsyncSession, host: Host) -> None:
    """Set transaction-local Postgres GUC for authenticated host requests."""
    await RLSService(db).set_host_context(host.id)


async def get_current_host(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Host:
    """Require a valid session token. Returns the authenticated Host or raises 401."""
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required",
        )

    host_service = HostService(db)
    host = await host_service.get_current_host_from_session(session_token)

    if not host:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    await apply_host_rls_context(db, host)
    return host


async def require_host_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Host:
    """Require a valid session token. Returns the authenticated Host or raises 401."""
    return await get_current_host(request, db)


async def optional_host_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[Host]:
    """Optionally authenticate via session token. Returns Host or None."""
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        return None

    try:
        host_service = HostService(db)
        host = await host_service.get_current_host_from_session(session_token)
        if host:
            await apply_host_rls_context(db, host)
        return host
    except Exception:
        return None


async def require_host_or_maintenance_job_secret(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Require either a valid host session (``X-Session-Token``) or maintenance job secret
    (``X-Maintenance-Job-Secret`` matching ``MAINTENANCE_JOB_SECRET``).
    """
    configured_secret = (settings.maintenance_job_secret or "").strip()
    provided_secret = (request.headers.get("X-Maintenance-Job-Secret") or "").strip()
    if (
        configured_secret
        and provided_secret
        and secrets.compare_digest(provided_secret, configured_secret)
    ):
        await RLSService(db).set_bypass("worker")
        return

    session_token = request.headers.get("X-Session-Token")
    if session_token:
        host_service = HostService(db)
        host = await host_service.get_current_host_from_session(session_token)
        if host:
            await apply_host_rls_context(db, host)
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


async def require_maintenance_job_secret_only(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Require ``X-Maintenance-Job-Secret`` matching ``MAINTENANCE_JOB_SECRET`` (no host session)."""
    configured_secret = (settings.maintenance_job_secret or "").strip()
    provided_secret = (request.headers.get("X-Maintenance-Job-Secret") or "").strip()
    if (
        configured_secret
        and provided_secret
        and secrets.compare_digest(provided_secret, configured_secret)
    ):
        await RLSService(db).set_bypass("worker")
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Maintenance job secret required",
    )
