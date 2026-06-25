"""Telegram webhook handler for HostForGuest A2A bot."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.a2a.orchestrator import A2AOrchestrator

logger = logging.getLogger(__name__)

_WELCOME_HR = (
    "👋 **Dobrodošli u HostForGuest!**\n\n"
    "Ja sam vaš AI asistent za upravljanje smještajem. Mogu vam pomoći s:\n\n"
    "🎫 **Grupe gostiju** — liste, ulaznice, QR kodovi\n"
    "✨ **Preporuke** — restorani, aktivnosti, degustacije vina\n"
    "📅 **Rezervacije** — pregled, check-in, check-out\n"
    "🎉 **Događaji** — koncerti, festivali, vikend planovi\n"
    "👤 **Račun** — pretplata, limiti, profil\n\n"
    "_Samo napišite što trebate — npr. \"preporuka Lovran\" ili \"moje rezervacije\"._"
)


class TelegramA2AHandler:
    """Handles Telegram updates and forwards text to the A2A orchestrator."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orchestrator = A2AOrchestrator(db)

    @property
    def bot_token(self) -> str:
        return (settings.telegram_bot_token or "").strip()

    def _api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str = "Markdown",
    ) -> bool:
        token = self.bot_token
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            logger.info("Telegram send skipped (no token): chat_id=%s text=%s", chat_id, text[:80])
            return False
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._api_base()}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text[:4096],
                        "parse_mode": parse_mode,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("Telegram sendMessage failed: %s %s", resp.status_code, resp.text)
                    return False
                return True
        except Exception as exc:
            logger.error("Telegram send_message error: %s", exc)
            return False

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Telegram webhook update payload."""
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"ok": True, "skipped": "no_message"}

        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        from_user = message.get("from") or {}
        telegram_id = from_user.get("id")
        text = (message.get("text") or "").strip()

        if not chat_id or not text:
            return {"ok": True, "skipped": "empty"}

        if text.startswith("/start"):
            await self.send_message(chat_id, _WELCOME_HR)
            return {"ok": True, "action": "welcome"}

        user_id = str(telegram_id or chat_id)
        result = await self.orchestrator.handle_message(
            text,
            user_id=user_id,
            telegram_id=int(telegram_id) if telegram_id else None,
        )
        reply = result.get("response") or "Nema odgovora."
        await self.send_message(chat_id, reply)
        return {
            "ok": True,
            "agent_id": result.get("agent_id"),
            "data": result.get("data"),
        }


async def register_telegram_webhook() -> Optional[Dict[str, Any]]:
    """Register Telegram webhook URL on API startup (if configured)."""
    token = (settings.telegram_bot_token or "").strip()
    url = (settings.telegram_webhook_url or "").strip()
    if not token or token == "YOUR_BOT_TOKEN_HERE" or not url:
        logger.info("Telegram webhook registration skipped (token or URL not set)")
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": url, "allowed_updates": ["message", "edited_message"]},
            )
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram webhook registered: %s", url)
            else:
                logger.warning("Telegram setWebhook failed: %s", data)
            return data
    except Exception as exc:
        logger.error("Telegram webhook registration error: %s", exc)
        return None
