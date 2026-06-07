"""Events pipeline uses cheap Gemini task API, not chat/heuristic routing."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from app.services.ai_service import AIService

pytestmark = pytest.mark.no_db


@pytest.mark.asyncio
async def test_generate_events_extraction_uses_env_model(monkeypatch):
    ai = AIService()
    captured: dict = {}

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kwargs):
            captured["config"] = kwargs
            return kwargs

    class FakeModels:
        async def generate_content(self, *, model, contents, config=None):
            captured["model"] = model
            captured["contents"] = contents
            captured["config_obj"] = config

            class R:
                text = '[{"title": "Test Fest 2026", "start_date": "2026-07-01"}]'

            return R()

    class FakeClient:
        aio = SimpleNamespace(models=FakeModels())

    async def fake_gemini_client(host_id):
        captured["host_id"] = host_id
        return FakeClient()

    monkeypatch.setenv("EVENTS_GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.delenv("GEMMA4_CF_CLIENT_ID", raising=False)
    monkeypatch.delenv("GEMMA4_CF_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(ai, "_get_gemini_client", fake_gemini_client)
    monkeypatch.setattr("app.services.ai_service._import_google_genai", lambda: (None, FakeTypes))

    result = await ai.generate_events_extraction(
        host_id="system",
        messages=[{"role": "user", "content": "extract events"}],
    )
    assert result["success"] is True
    assert captured["model"] == "gemini-2.0-flash"
    assert "Human: extract events" in captured["contents"]
    assert "Test Fest" in result["response"]
