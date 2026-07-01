"""A2A orchestrator — intent routing to specialized HFG agents."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.services.rls_service import RLSService
from app.services.a2a.agent_wrappers import build_all_agents
from app.services.a2a.guest_agent_wrappers import build_all_guest_agents
from app.services.a2a.messages import host_welcome_message_hr
from app.services.a2a.intent_classifier import A2AIntentClassifier
from app.services.a2a.registry import AgentRegistry
from app.services.ai_service_fallback import AIServiceWithFallback

logger = logging.getLogger(__name__)

# Shared in-memory guest/host session store (keyed by telegram user_id)
_GLOBAL_A2A_SESSIONS: Dict[str, Dict[str, Any]] = {}


class A2AOrchestrator:
    _sessions: Dict[str, Dict[str, Any]] = {}
    """Routes user messages to the correct HFG agent."""

    def __init__(
        self,
        db: Optional[AsyncSession],
        *,
        ai_service: Optional[AIServiceWithFallback] = None,
        intent_classifier: Optional[A2AIntentClassifier] = None,
    ) -> None:
        self.db = db
        self.registry = AgentRegistry()
        for agent in build_all_agents(db):
            self.registry.register_agent(agent)
        for agent in build_all_guest_agents(db):
            self.registry.register_agent(agent)
        self._sessions = _GLOBAL_A2A_SESSIONS
        self._intent_classifier = intent_classifier or A2AIntentClassifier(ai_service=ai_service)

    async def _classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        return await self._intent_classifier.classify_intent(message, context)

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
            async with RLSService(self.db).worker_bypass():
                stmt = select(Host).where(Host.telegram_id == telegram_id)
                result = await self.db.execute(stmt)
                host = result.scalar_one_or_none()
                return host.id if host else None
        except Exception as exc:
            logger.error("resolve_host_id failed: %s", exc)
            return None

    async def handle_link(
        self,
        message: str,
        *,
        telegram_id: int,
    ) -> Dict[str, Any]:
        """Handle /link CODE — self-service Telegram pairing."""
        if not self.db:
            return {
                "response": "⚠️ Povezivanje nije dostupno. Pokušajte kasnije.",
                "agent_id": "host-dashboard-hfg",
                "data": None,
                "action": "link_error",
            }

        parts = (message or "").strip().split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""

        from app.services.telegram_pairing_service import TelegramPairingService

        svc = TelegramPairingService(self.db)
        result = await svc.link_by_code(telegram_id, code)

        if result.get("ok"):
            return {
                "response": result["response"],
                "agent_id": "host-dashboard-hfg",
                "data": {"host_id": str(result.get("host_id"))} if result.get("host_id") else None,
                "action": "link_success",
            }

        action = "link_already_linked" if result.get("already_linked") else "link_error"
        return {
            "response": result.get("response", "Kod nije valjan ili je istekao. Idite na web za novi kod."),
            "agent_id": "host-dashboard-hfg",
            "data": None,
            "action": action,
        }

    async def bind_telegram_host(self, telegram_id: int, host_id: uuid.UUID) -> bool:
        if not self.db:
            return False
        try:
            async with RLSService(self.db).worker_bypass():
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

    async def handle_start(
        self,
        message: str,
        *,
        user_id: str,
        telegram_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle /start — guest ticket deep link or host welcome."""
        text = (message or "").strip()
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        is_guest_ticket = bool(payload) and (
            payload.lower().startswith("ticket_") or len(payload) >= 6
        )

        context = self._get_context(user_id)
        if telegram_id is not None:
            context["telegram_id"] = telegram_id

        if is_guest_ticket:
            agent_id = "guest-welcome-hfg"
            agent = self.registry.get_agent(agent_id)
            if not agent:
                return {
                    "response": "⚠️ Guest agent nije dostupan.",
                    "agent_id": agent_id,
                    "data": None,
                }
            try:
                result = await agent.execute(message, None, context)
            except Exception as exc:
                logger.exception("Guest start failed: %s", exc)
                return {
                    "response": "⚠️ Greška pri otvaranju ulaznice. Pokušajte ponovo.",
                    "agent_id": agent_id,
                    "data": None,
                }
            self._sessions[self._session_key(user_id)] = context
            return {
                "response": result.get("response", ""),
                "agent_id": agent_id,
                "data": result.get("data"),
                "action": "guest_welcome",
            }

        host_id = None
        if telegram_id is not None:
            host_id = await self.resolve_host_id(telegram_id)
        if host_id:
            context["role"] = "host"
            context.pop("guest_group_id", None)

        return {
            "response": host_welcome_message_hr(),
            "agent_id": "host-dashboard-hfg",
            "data": None,
            "action": "welcome",
        }

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
        stripped = (message or "").strip()
        lower = stripped.lower()

        if lower.startswith("/start"):
            return await self.handle_start(
                message,
                user_id=user_id,
                telegram_id=telegram_id,
            )

        if lower.startswith("/link"):
            if telegram_id is None:
                return {
                    "response": "⚠️ Telegram ID nije dostupan. Pokušajte ponovo iz Telegram aplikacije.",
                    "agent_id": "host-dashboard-hfg",
                    "data": None,
                    "action": "link_error",
                }
            return await self.handle_link(stripped, telegram_id=telegram_id)

        context = self._get_context(user_id)
        if telegram_id is not None:
            context["telegram_id"] = telegram_id

        agent_id = await self._classify_intent(message, context)

        resolved_host = host_id
        is_guest = context.get("role") == "guest" or context.get("guest_group_id")
        if not is_guest:
            if resolved_host is None and telegram_id is not None:
                resolved_host = await self.resolve_host_id(telegram_id)
            if resolved_host:
                context["role"] = "host"

        agent = self.registry.get_agent(agent_id)
        if not agent:
            return {
                "response": "⚠️ Agent nije dostupan. Pokušajte ponovo.",
                "agent_id": agent_id,
                "data": None,
            }

        exec_host_id = None if is_guest else resolved_host

        if exec_host_id and self.db:
            await RLSService(self.db).set_host_context(exec_host_id)

        try:
            result = await agent.execute(message, exec_host_id, context)
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
