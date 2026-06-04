"""
Gemini-based extraction of structured local events from tourism HTML.

Primary ingestion path: model interprets page text; code only validates JSON/schema.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, List, Optional

from bs4 import BeautifulSoup

from app.scraping.events.filters import filter_event_drafts, is_valid_event_draft_title
from app.scraping.events.normalizer import infer_tags, parse_hr_date_range
from app.scraping.events.schemas.local_event import LocalEventDraft
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You extract REAL public events (festivals, concerts, markets, sports, cultural days)
from Croatian tourism board page text. Return ONLY a JSON array. No markdown.

Each item:
{
  "title": "string (required, min 4 chars)",
  "description": "string",
  "url": "string or null",
  "start_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "end_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "start_time": "HH:MM 24h or null (e.g. 18:00)",
  "end_time": "HH:MM 24h or null",
  "city": "string or null",
  "venue_name": "string or null",
  "tags": ["festival", "music", ...]
}

Exclude: contact pages, how to get here, accommodation tips, phone, email, generic navigation.
Include only happenings visitors can attend with a date or clear seasonal window."""

DETAIL_EXTRACTION_SYSTEM = """You extract schedule and venue facts for ONE Croatian public event from a detail page.
Return ONLY a JSON object (not an array). No markdown.

{
  "title": "string",
  "description": "string (1-3 sentences)",
  "start_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "end_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "start_time": "HH:MM 24h or null",
  "end_time": "HH:MM 24h or null",
  "city": "string or null",
  "venue_name": "string or null",
  "tags": ["festival", "music", ...]
}

Rules:
- Prefer explicit dates/times from the page (datum, vrijeme, sat, kalendar).
- Multi-day festivals: set start_date and end_date.
- If only a month/year is known, use the first plausible day in that month.
- If no reliable date exists, set start_date and end_date to null.
- Do not invent dates."""

TEXT_METADATA_SYSTEM = """You infer event schedule metadata from short Croatian event copy.
Return ONLY a JSON object (not an array). No markdown.

{
  "start_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "end_date": "YYYY-MM-DD or DD.MM.YYYY or null",
  "start_time": "HH:MM 24h or null",
  "end_time": "HH:MM 24h or null",
  "city": "string or null",
  "venue_name": "string or null"
}

Only fill fields clearly supported by the text. Do not guess."""


class EventExtractionRefiner:
    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai = ai_service or AIService()

    def html_to_text(self, html: str, max_chars: Optional[int] = None) -> str:
        if max_chars is None:
            import os

            max_chars = int(os.getenv("EVENTS_HTML_MAX_CHARS", "8000"))
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        return text[:max_chars]

    async def extract_from_html(
        self,
        html: str,
        *,
        page_url: str,
        city: Optional[str] = None,
        region: Optional[str] = None,
        host_id: str = "system",
    ) -> List[LocalEventDraft]:
        """Parse events from listing page HTML using Gemini (EVENTS_GEMINI_MODEL)."""
        text = self.html_to_text(html)
        if len(text) < 80:
            return []

        prompt = (
            f"Source page URL: {page_url}\n"
            f"Region: {region or 'Croatia'}\n"
            f"City focus: {city or 'unknown'}\n\n"
            f"Page text:\n{text}"
        )

        raw = await self._call_llm(prompt, host_id)
        drafts = self._parse_llm_events(raw, page_url=page_url, city=city, region=region)
        return filter_event_drafts(drafts)

    async def extract_detail_from_html(
        self,
        html: str,
        *,
        page_url: str,
        hint_title: str,
        city: Optional[str] = None,
        region: Optional[str] = None,
        host_id: str = "system",
    ) -> Optional[LocalEventDraft]:
        """Extract one event schedule from a detail page."""
        text = self.html_to_text(html, max_chars=int(__import__("os").getenv("EVENTS_DETAIL_HTML_MAX_CHARS", "12000")))
        if len(text) < 60:
            return None
        prompt = (
            f"Detail page URL: {page_url}\n"
            f"Expected event title: {hint_title}\n"
            f"Region: {region or 'Croatia'}\n"
            f"City focus: {city or 'unknown'}\n\n"
            f"Page text:\n{text}"
        )
        raw = await self._call_llm(prompt, host_id, system=DETAIL_EXTRACTION_SYSTEM)
        draft = self._parse_llm_single_event(
            raw,
            page_url=page_url,
            city=city,
            region=region,
            fallback_title=hint_title,
        )
        return draft

    async def extract_metadata_from_text(
        self,
        *,
        title: str,
        description: str = "",
        city: Optional[str] = None,
        region: Optional[str] = None,
        host_id: str = "system",
    ) -> Optional[LocalEventDraft]:
        """Infer dates/venue from title+description when no detail URL exists."""
        blob = f"{title}\n{description}".strip()
        if len(blob) < 8:
            return None
        prompt = (
            f"Region: {region or 'Croatia'}\n"
            f"City focus: {city or 'unknown'}\n\n"
            f"Event copy:\n{blob[:4000]}"
        )
        raw = await self._call_llm(prompt, host_id, system=TEXT_METADATA_SYSTEM)
        return self._parse_llm_single_event(
            raw,
            page_url="",
            city=city,
            region=region,
            fallback_title=title,
            description_fallback=description,
        )

    async def _call_llm(self, prompt: str, host_id: str, system: Optional[str] = None) -> str:
        system_prompt = system or EXTRACTION_SYSTEM
        try:
            result = await self.ai.generate_events_extraction(
                host_id=host_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            if isinstance(result, dict) and result.get("success"):
                return str(result.get("response") or "[]")
            logger.warning(
                "Event extraction Gemini failed: %s",
                result.get("error") if isinstance(result, dict) else result,
            )
            return "[]"
        except Exception as exc:
            logger.warning("Event extraction LLM unavailable: %s", exc)
            return "[]"

    def _load_llm_json(self, raw: str) -> Any:
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            obj = re.search(r"\{[\s\S]*\}", text)
            arr = re.search(r"\[[\s\S]*\]", text)
            candidate = obj.group(0) if obj else (arr.group(0) if arr else None)
            if not candidate:
                return None
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

    def _draft_from_llm_item(
        self,
        item: dict,
        *,
        page_url: str,
        city: Optional[str],
        region: Optional[str],
        fallback_title: Optional[str] = None,
        description_fallback: str = "",
    ) -> Optional[LocalEventDraft]:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or fallback_title or "").strip()
        if not is_valid_event_draft_title(title):
            return None
        start_raw = item.get("start_date") or item.get("start_at")
        end_raw = item.get("end_date") or item.get("end_at")
        start_at, end_at = parse_hr_date_range(
            f"{start_raw} – {end_raw}" if start_raw and end_raw else str(start_raw or "")
        )
        if start_raw and not start_at:
            start_at = self._parse_iso_date(str(start_raw))
        if end_raw and not end_at:
            end_at = self._parse_iso_date(str(end_raw))
        start_at = self._merge_time(start_at, item.get("start_time"))
        end_at = self._merge_time(end_at, item.get("end_time"))

        desc = str(item.get("description") or description_fallback or title)[:2000]
        url = item.get("url")
        if url and str(url).startswith("/") and page_url:
            from urllib.parse import urljoin

            url = urljoin(page_url, str(url))
        elif not url and page_url:
            url = page_url

        tags = item.get("tags") or infer_tags(f"{title} {desc}")
        if isinstance(tags, str):
            tags = [tags]

        return LocalEventDraft(
            title=title[:500],
            description=desc,
            url=str(url) if url else None,
            start_at=start_at,
            end_at=end_at or start_at,
            city=item.get("city") or city,
            region=item.get("region") or region,
            venue_name=item.get("venue_name"),
            tags=[str(t) for t in tags][:8],
            external_id=re.sub(r"[^a-z0-9]+", "-", title.lower())[:120],
            confidence=0.88 if start_at else 0.65,
        )

    def _parse_llm_single_event(
        self,
        raw: str,
        *,
        page_url: str,
        city: Optional[str],
        region: Optional[str],
        fallback_title: str,
        description_fallback: str = "",
    ) -> Optional[LocalEventDraft]:
        data = self._load_llm_json(raw)
        if data is None:
            return None
        if isinstance(data, list):
            if not data:
                return None
            data = data[0]
        if not isinstance(data, dict):
            return None
        return self._draft_from_llm_item(
            data,
            page_url=page_url,
            city=city,
            region=region,
            fallback_title=fallback_title,
            description_fallback=description_fallback,
        )

    def _parse_llm_events(
        self,
        raw: str,
        *,
        page_url: str,
        city: Optional[str],
        region: Optional[str],
    ) -> List[LocalEventDraft]:
        data = self._load_llm_json(raw)
        if data is None:
            return []
        if isinstance(data, dict) and "events" in data:
            data = data["events"]
        if not isinstance(data, list):
            return []

        out: List[LocalEventDraft] = []
        for item in data:
            draft = self._draft_from_llm_item(
                item,
                page_url=page_url,
                city=city,
                region=region,
            )
            if draft:
                out.append(draft)
        return out

    def _parse_iso_date(self, value: str) -> Optional[datetime]:
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(value[:10], fmt)
                return dt.replace(hour=12, minute=0, second=0)
            except ValueError:
                continue
        return None

    def _merge_time(self, dt: Optional[datetime], raw_time: Any) -> Optional[datetime]:
        if not dt or not raw_time:
            return dt
        from app.scraping.events.normalizer import parse_time_from_text

        t = parse_time_from_text(str(raw_time))
        if not t:
            return dt
        return dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
