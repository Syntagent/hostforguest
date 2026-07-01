"""HostForGuest A2A module exports."""

from app.services.a2a.agent_card import AgentCard, ALL_HFG_AGENT_CARDS, GUEST_AGENT_CARDS, HFG_AGENT_CARDS
from app.services.a2a.orchestrator import A2AOrchestrator
from app.services.a2a.registry import AgentRegistry
from app.services.a2a.telegram_handler import TelegramA2AHandler, register_telegram_webhook

__all__ = [
    "AgentCard",
    "HFG_AGENT_CARDS",
    "GUEST_AGENT_CARDS",
    "ALL_HFG_AGENT_CARDS",
    "AgentRegistry",
    "A2AOrchestrator",
    "TelegramA2AHandler",
    "register_telegram_webhook",
]
