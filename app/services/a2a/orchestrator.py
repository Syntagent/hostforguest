"""A2A orchestrator — intent routing to specialized HFG agents."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.services.a2a.agent_wrappers import build_all_agents
from app.services.a2a.registry import AgentRegistry

logger = logging.getLogger(__name__)

# Keyword → agent id (first match wins; default guest-ticket-hfg)
_INTENT_RULES: list[tuple[list[str], str]] = [
    (["ticket", "guest", "qr", "checkin", "gost", "ulaznica", "grupa"], "guest-ticket-hfg"),
    (["preporuka", "recommend", "što raditi", "sto raditi", "restoran", "vino"], "recommendations-hfg"),
    (["booking", "rezervacija", "dolazak", "odlazak", "checkout"], "bookings-hfg"),
    (["događaj", "dogadaj", "event", "vikend", "koncert", "festival"], "events-hfg"),
    (["račun", "racun", "account", "subscription", "plan", "limit", "pretplata", "usage", "korištenje"], "host-dashboard-hfg"),
]


class A2AOrchestrator:
    """Routes user messages to the correct HFG agent."""

    def __init__(self, db: Optional[AsyncSession]) -> None:
        self.db = db
        self.registry = AgentRegistry()
        for agent in build_all_agents(db):
            self.registry.register_agent(agent)
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _classify_intent(self, message: str) -> str:
        text = (message or "").lower()
        for keywords, agent_id in _INTENT_RULES:
            for kw in keywords:
                if kw in text:
                    return agent_id
        return "guest-ticket-hfg"

    def _session_key(self, user_id: str) -> str:
        return str(user_id)

    def _get_context(self, user_id: str) -> Dict[str, Any]:
        key = self._session_key(user_id)
        if key not in self._sessions:
            self._sessions[key] = {"last_command": None, "last_context": {}}
        return self._sessions[key]

    async def resolve_host_id(self, telegram_id: int) -> Optional[uuid.UUID]:
        if not self.db:
            return None
        try:
            stmt = select(Host).where(Host.telegram_id == telegram_id)
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()
            return host.id if host else None
        except Exception as exc:
            logger.error("resolve_host_id failed: %s", exc)
            return None

    async def bind_telegram_host(self, telegram_id: int, host_id: uuid.UUID) -> bool:
        if not self.db:
            return False
        try:
            stmt = select(Host).where(Host.id == host_id)
            result = await self.db.execute(stmt)
            host = result.scalar_one_or_none()
            if not host:
                return False
            host.telegram_id = telegram_id
            await self.db.commit()
            return True
        except Exception as exc:
            logger.error("bind_telegram_host failed: %s", exc)
            await self.db.rollback()
            return False

    async def handle_message(
        self,
        message: str,
        *,
        user_id: str,
        telegram_id: Optional[int] = None,
        host_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Classify intent, dispatch to agent, return structured response.

        Returns dict with keys: response, agent_id, data (optional).
        """
        agent_id = self._classify_intent(message)
        context = self._get_context(user_id)

        resolved_host = host_id
        if resolved_host is None and telegram_id is not None:
            resolved_host = await self.resolve_host_id(telegram_id)

        agent = self.registry.get_agent(agent_id)
        if not agent:
            return {
                "response": "⚠️ Agent nije dostupan. Pokušajte ponovo.",
                "agent_id": agent_id,
                "data": None,
            }

        try:
            result = await agent.execute(message, resolved_host, context)
        except Exception as exc:
            logger.exception("Agent %s failed: %s", agent_id, exc)
            return {
                "response": (
                    f"⚠️ Došlo je do greške u agentu *{agent_id}*. "
                    "Pokušajte kasnije ili kontaktirajte podršku."
                ),
                "agent_id": agent_id,
                "data": None,
            }

        self._sessions[self._session_key(user_id)] = context
        return {
            "response": result.get("response", ""),
            "agent_id": agent_id,
            "data": result.get("data"),
        }
