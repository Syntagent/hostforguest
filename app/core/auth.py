"""
Shared authentication dependencies for FastAPI endpoints.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.host_service import HostService
from app.models.host import Host

logger = logging.getLogger(__name__)


async def require_host_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Host:
    """Require a valid session token. Returns the authenticated Host or raises 401."""
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    host_service = HostService(db)
    host = await host_service.get_current_host_from_session(session_token)

    if not host:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return host


async def optional_host_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[Host]:
    """Optionally authenticate via session token. Returns Host or None."""
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        return None

    try:
        host_service = HostService(db)
        return await host_service.get_current_host_from_session(session_token)
    except Exception:
        return None
