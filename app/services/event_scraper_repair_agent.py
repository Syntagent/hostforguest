"""
Suggests scraper repairs when event sources fail health checks (LLM-assisted, not auto-applied).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

REPAIR_SYSTEM = """You help fix Croatian tourism event listing scrapers.
Given HTML snippet, error message, and current selectors, suggest improved CSS selectors
and a one-paragraph explanation. Return JSON: {"item_selector": str, "date_selector": str, "explanation": str}"""


class EventScraperRepairAgent:
    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai = ai_service or AIService()

    async def suggest_repair(
        self,
        *,
        slug: str,
        last_error: str,
        html_snippet: str,
        current_selectors: Dict[str, str],
        host_id: str = "system",
    ) -> Dict[str, Any]:
        prompt = (
            f"Source slug: {slug}\n"
            f"Error: {last_error}\n"
            f"Current selectors: {current_selectors}\n"
            f"HTML sample (truncated):\n{html_snippet[:4000]}"
        )
        try:
            result = await self.ai.generate_events_extraction(
                host_id=host_id,
                messages=[
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            )
            text = result.get("response") if isinstance(result, dict) else str(result)
            return {"success": True, "suggestion": text, "slug": slug}
        except Exception as exc:
            logger.warning("Repair agent unavailable: %s", exc)
            return {
                "success": False,
                "slug": slug,
                "message": "Repair suggestions unavailable; check scraper fixtures and site DOM manually.",
                "error": str(exc),
            }
