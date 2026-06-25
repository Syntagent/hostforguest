"""A2A protocol API — Telegram bot orchestration and agent discovery."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.a2a.agent_card import HFG_AGENT_CARDS
from app.services.a2a.orchestrator import A2AOrchestrator
from app.services.a2a.telegram_handler import TelegramA2AHandler

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(default="api-user")
    telegram_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    data: Optional[Dict[str, Any]] = None


class AgentsResponse(BaseModel):
    agents: List[Dict[str, Any]]
    count: int


@router.get("/health")
async def a2a_health() -> Dict[str, Any]:
    """A2A subsystem health check."""
    return {
        "status": "healthy",
        "agents_registered": len(HFG_AGENT_CARDS),
        "service": "a2a",
    }


@router.get("/agents", response_model=AgentsResponse)
async def list_agents() -> AgentsResponse:
    """Return all registered HFG agent cards."""
    cards = [card.to_dict() for card in HFG_AGENT_CARDS.values()]
    return AgentsResponse(agents=cards, count=len(cards))


@router.post("/chat", response_model=ChatResponse)
async def a2a_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Route a text message through the A2A orchestrator (non-Telegram clients)."""
    orchestrator = A2AOrchestrator(db)
    result = await orchestrator.handle_message(
        body.message,
        user_id=body.user_id,
        telegram_id=body.telegram_id,
    )
    return ChatResponse(
        response=result.get("response", ""),
        agent_id=result.get("agent_id", ""),
        data=result.get("data"),
    )


@router.post("/telegram-webhook")
async def telegram_webhook(
    update: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Telegram Bot API webhook endpoint."""
    handler = TelegramA2AHandler(db)
    return await handler.handle_update(update)
