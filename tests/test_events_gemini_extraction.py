"""Events pipeline uses cheap Gemini task API, not chat/heuristic routing."""

from __future__ import annotations

import pytest

from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_generate_events_extraction_uses_env_model(monkeypatch):
    ai = AIService()
    captured: dict = {}

    async def fake_gemini(host_id, model_name):
        captured["model"] = model_name
        captured["host_id"] = host_id

        class FakeModel:
            async def generate_content_async(self, _msg, generation_config=None):
                class R:
                    text = '[{"title": "Test Fest 2026", "start_date": "2026-07-01"}]'

                return R()

        return FakeModel()

    monkeypatch.setenv("EVENTS_GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(ai, "_get_gemini_model", fake_gemini)

    result = await ai.generate_events_extraction(
        host_id="system",
        messages=[{"role": "user", "content": "extract events"}],
    )
    assert result["success"] is True
    assert captured["model"] == "gemini-2.0-flash"
    assert "Test Fest" in result["response"]
