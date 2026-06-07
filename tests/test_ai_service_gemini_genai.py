"""Gemini event extraction uses google.genai lazily and fails cleanly without keys."""

from __future__ import annotations

import pytest
import subprocess
import sys

from app.services.ai_service import AIService

pytestmark = pytest.mark.no_db


@pytest.mark.asyncio
async def test_events_extraction_without_ai_keys_does_not_import_gemini(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMMA4_CF_CLIENT_ID", raising=False)
    monkeypatch.delenv("GEMMA4_CF_CLIENT_SECRET", raising=False)

    def fail_import():
        raise AssertionError("Gemini SDK should not be imported without an API key")

    monkeypatch.setattr("app.services.ai_service._import_google_genai", fail_import)

    result = await AIService().generate_events_extraction(
        [{"role": "user", "content": "Extract events from this page"}],
        host_id="system",
    )

    assert result["success"] is False
    assert "Gemini client not available" in result["error"]


def test_messages_to_text_preserves_chat_roles():
    text = AIService()._messages_to_text(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "Find events."},
            {"role": "assistant", "content": "[]"},
        ]
    )

    assert "System: Return JSON only." in text
    assert "Human: Find events." in text
    assert "Assistant: []" in text


def test_ai_service_import_does_not_load_openai_sdk():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.services.ai_service; print('openai' in sys.modules)",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "False"
