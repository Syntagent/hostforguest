"""A2A protocol API — Telegram bot orchestration and agent discovery."""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_host, optional_host_session
from app.models.host import Host
from app.core.config import settings
from app.core.database import get_db
from app.services.a2a.agent_card import ALL_HFG_AGENT_CARDS, GUEST_AGENT_CARDS
from app.services.a2a.orchestrator import A2AOrchestrator
from app.services.a2a.telegram_handler import TelegramA2AHandler
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)
router = APIRouter()


def _allow_unconfigured_telegram_webhook() -> bool:
    """Development and pytest may omit TELEGRAM_WEBHOOK_SECRET; production must not."""
    if settings.is_development:
        return True
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TOURISTGUIDE_PYTEST"))


def _verify_telegram_webhook_secret(request: Request) -> None:
    """Reject webhook calls when TELEGRAM_WEBHOOK_SECRET is set but header is missing/wrong."""
    configured = (settings.telegram_webhook_secret or "").strip()
    if not configured:
        if not _allow_unconfigured_telegram_webhook():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram webhook secret not configured",
            )
        return
    provided = (request.headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
    if provided and secrets.compare_digest(provided, configured):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Telegram webhook secret",
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(default="api-user")
    telegram_id: Optional[int] = None
    host_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    data: Optional[Dict[str, Any]] = None
    action: Optional[str] = None


class AgentsResponse(BaseModel):
    agents: List[Dict[str, Any]]
    count: int


@router.get("/health")
async def a2a_health() -> Dict[str, Any]:
    """A2A subsystem health check."""
    return {
        "status": "healthy",
        "agents_registered": len(ALL_HFG_AGENT_CARDS),
        "service": "a2a",
    }


@router.get("/agents", response_model=AgentsResponse)
async def list_agents(
    request: Request,
    current_host: Optional[Host] = Depends(optional_host_session),
) -> AgentsResponse:
    """Return guest agent cards publicly; full registry for host session or maintenance."""
    if current_host is not None or _is_maintenance_job_request(request):
        registry = ALL_HFG_AGENT_CARDS
    else:
        registry = GUEST_AGENT_CARDS
    if current_host is not None or _is_maintenance_job_request(request):
        cards = [card.to_dict() for card in registry.values()]
    else:
        cards = [card.to_public_dict() for card in registry.values()]
    return AgentsResponse(agents=cards, count=len(cards))


def _is_maintenance_job_request(request: Request) -> bool:
    configured = (settings.maintenance_job_secret or "").strip()
    provided = (request.headers.get("X-Maintenance-Job-Secret") or "").strip()
    return bool(
        configured and provided and secrets.compare_digest(provided, configured)
    )


@router.post("/chat", response_model=ChatResponse)
async def a2a_chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Route a text message through the A2A orchestrator (non-Telegram clients)."""
    orchestrator = A2AOrchestrator(db)
    host_id = None
    telegram_id = body.telegram_id

    if _is_maintenance_job_request(request):
        if not body.host_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="host_id required for maintenance A2A chat",
            )
        host_id = uuid.UUID(body.host_id)
        await RLSService(db).set_host_context(host_id)
    else:
        current_host: Host = await get_current_host(request, db)
        host_id = current_host.id
        if body.telegram_id is not None:
            linked = current_host.telegram_id
            if linked is not None and body.telegram_id != linked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="telegram_id does not match authenticated host",
                )
        telegram_id = current_host.telegram_id

    result = await orchestrator.handle_message(
        body.message,
        user_id=body.user_id,
        telegram_id=telegram_id,
        host_id=host_id,
    )
    return ChatResponse(
        response=result.get("response", ""),
        agent_id=result.get("agent_id", ""),
        data=result.get("data"),
        action=result.get("action"),
    )


@router.post("/telegram-webhook")
async def telegram_webhook(
    request: Request,
    update: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Telegram Bot API webhook endpoint."""
    _verify_telegram_webhook_secret(request)
    async with RLSService(db).worker_bypass():
        handler = TelegramA2AHandler(db)
        return await handler.handle_update(update)
