"""EventExtractionRefiner parses LLM JSON into LocalEventDraft rows."""

from __future__ import annotations

import pytest

from app.services.event_extraction_refiner import EventExtractionRefiner


def test_parse_llm_events_json_array():
    refiner = EventExtractionRefiner()
    raw = """[
      {"title": "Marunada 2026", "description": "Chestnut festival", "start_date": "10.10.2026", "end_date": "12.10.2026", "city": "Lovran", "tags": ["festival"]},
      {"title": "X", "description": "phone"}
    ]"""
    drafts = refiner._parse_llm_events(
        raw, page_url="https://visitlovran.com/dogadanja/", city="Lovran", region="Kvarner"
    )
    assert len(drafts) == 1
    assert drafts[0].title == "Marunada 2026"
    assert drafts[0].start_at is not None
    assert drafts[0].city == "Lovran"


@pytest.mark.asyncio
async def test_extract_uses_llm_when_mocked(monkeypatch):
    refiner = EventExtractionRefiner()

    async def fake_llm(prompt, host_id):
        return '[{"title": "Jerry Ricks Blues Festival", "start_date": "2026-07-15", "city": "Lovran"}]'

    async def fake_gemini(*, host_id, messages):
        return {"success": True, "response": await fake_llm("", host_id)}

    monkeypatch.setattr(refiner.ai, "generate_events_extraction", fake_gemini)
    html = "<html><body>" + ("<p>Lovran events calendar with festivals and concerts.</p>\n" * 6)
    html += "<h3>Jerry Ricks Blues Festival — 15.7.2026</h3></body></html>"
    drafts = await refiner.extract_from_html(
        html,
        page_url="https://visitlovran.com/dogadanja/",
        city="Lovran",
    )
    assert len(drafts) == 1
    assert "Blues" in drafts[0].title
