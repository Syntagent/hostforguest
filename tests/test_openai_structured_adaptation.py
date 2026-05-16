"""OpenAI structured JSON path (used by adaptation analyze when provider is openai)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.adaptation_service import AdaptationAnalyzeResultModel
from app.services.ai_service_fallback import AIServiceWithFallback


@pytest.mark.asyncio
async def test_generate_structured_openai_json_object_success(monkeypatch):
    settings = MagicMock()
    svc = AIServiceWithFallback(settings)

    svc.get_ai_config_for_host_with_fallback = AsyncMock(
        return_value={
            "preferred_ai_provider": "openai",
            "openai_model": "gpt-4o-mini",
            "openai_temperature": "0.2",
        }
    )

    payload = AdaptationAnalyzeResultModel(
        vision_summary="Kitchen with dated cabinets",
        risks_and_checks=["Verify load-bearing before removing walls"],
        mood_board_text="Warm minimal",
        bom_lines=[],
        after_direction_text="Refreshed fronts and LED under-cabinet lighting.",
    ).model_dump()

    fake_client = MagicMock()

    async def fake_create(**kwargs):
        assert kwargs.get("response_format") == {"type": "json_object"}
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=40, total_tokens=50)
        return resp

    fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)
    monkeypatch.setattr(svc, "_get_openai_client", AsyncMock(return_value=fake_client))

    out = await svc.generate_structured_response(
        "00000000-0000-0000-0000-000000000001",
        [{"role": "user", "content": "Run adaptation analyze"}],
        context=None,
        response_schema=AdaptationAnalyzeResultModel,
        image_parts=None,
    )

    assert out["success"] is True
    assert out["provider"] == "openai_structured"
    assert out["structured_data"]["vision_summary"].startswith("Kitchen")


@pytest.mark.asyncio
async def test_generate_structured_openai_sends_vision_parts(monkeypatch):
    settings = MagicMock()
    svc = AIServiceWithFallback(settings)
    svc.get_ai_config_for_host_with_fallback = AsyncMock(
        return_value={
            "preferred_ai_provider": "openai",
            "openai_model": "gpt-4o-mini",
            "openai_temperature": "0.2",
        }
    )

    payload = AdaptationAnalyzeResultModel(
        vision_summary="Bathroom tiles visible",
        risks_and_checks=[],
        mood_board_text="Spa calm",
        bom_lines=[],
        after_direction_text="Stone-look porcelain and matte black fixtures.",
    ).model_dump()

    captured: dict = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        msgs = kwargs["messages"]
        user = msgs[-1]
        assert user["role"] == "user"
        assert isinstance(user["content"], list)
        assert user["content"][0]["type"] == "text"
        assert any(p.get("type") == "image_url" for p in user["content"])
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
        resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)
    monkeypatch.setattr(svc, "_get_openai_client", AsyncMock(return_value=fake_client))

    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20

    out = await svc.generate_structured_response(
        "00000000-0000-0000-0000-000000000001",
        [{"role": "user", "content": "Analyze with photo"}],
        context=None,
        response_schema=AdaptationAnalyzeResultModel,
        image_parts=[("image/jpeg", jpeg_bytes)],
    )

    assert out["success"] is True
    assert captured.get("max_tokens") == 4096
