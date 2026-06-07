"""Adaptation multimodal vision: URL fetch rules and Gemini payload shape."""

from unittest.mock import patch

import pytest

from app.services.adaptation_service import fetch_image_bytes_for_adaptation_vision
from app.services.ai_service_fallback import AIServiceWithFallback

pytestmark = pytest.mark.no_db


def test_gemini_structured_payload_text_only():
    p = AIServiceWithFallback._gemini_structured_content_payload("hello", None)
    assert p == "hello"
    p2 = AIServiceWithFallback._gemini_structured_content_payload("hello", [])
    assert p2 == "hello"


def test_gemini_structured_payload_multimodal_list():
    p = AIServiceWithFallback._gemini_structured_content_payload(
        "prompt",
        [("image/png", b"\x89PNG\r\n\x1a"), ("image/jpeg", b"\xff\xd8\xff")],
    )
    assert isinstance(p, list)
    assert p[0] == "prompt"
    assert p[1] == {"mime_type": "image/png", "data": b"\x89PNG\r\n\x1a"}
    assert p[2]["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_fetch_adaptation_vision_skips_non_http():
    assert await fetch_image_bytes_for_adaptation_vision([]) == []
    assert await fetch_image_bytes_for_adaptation_vision(["file:///etc/passwd"]) == []
    assert await fetch_image_bytes_for_adaptation_vision(["ftp://x/y"]) == []


@pytest.mark.asyncio
async def test_fetch_adaptation_vision_accepts_https_image():
    class FakeResp:
        status_code = 200
        content = b"\xff\xd8\xff\xe0"
        headers = {"content-type": "image/jpeg"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            assert url.startswith("https://")
            return FakeResp()

    with patch("app.services.adaptation_service.httpx.AsyncClient", return_value=FakeClient()):
        out = await fetch_image_bytes_for_adaptation_vision(["https://cdn.example.com/room.jpg"])
    assert len(out) == 1
    assert out[0][0] == "image/jpeg"
    assert out[0][1].startswith(b"\xff\xd8")


@pytest.mark.asyncio
async def test_fetch_adaptation_vision_rejects_non_image_content_type():
    class FakeResp:
        status_code = 200
        content = b"<html></html>"
        headers = {"content-type": "text/html"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            return FakeResp()

    with patch("app.services.adaptation_service.httpx.AsyncClient", return_value=FakeClient()):
        out = await fetch_image_bytes_for_adaptation_vision(["https://example.com/page"])
    assert out == []
