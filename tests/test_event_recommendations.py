"""Live-API checks for guest event recommendations (optional; needs running API)."""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_API_TESTS", "").strip() not in ("1", "true", "yes"),
    reason="Set RUN_LIVE_API_TESTS=1 with API_BASE_URL and BEN_GUEST_ACCESS_CODE",
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8006/api").rstrip("/")
CODE = os.getenv("BEN_GUEST_ACCESS_CODE", os.getenv("E2E_GUEST_ACCESS_CODE", "Q4EF3BFW"))


@pytest.fixture
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)


def test_event_recommendations_returns_scored_list(client: httpx.Client) -> None:
    r = client.get(f"/v1/guest-groups/access/{CODE}/event-recommendations", params={"limit": 10})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert body.get("city")
    recs = body.get("recommendations") or []
    assert isinstance(recs, list)
    if recs:
        first = recs[0]
        assert "title" in first
        assert "relevance_score" in first
        assert "why_recommended" in first
        assert "plan_hint" in first
        assert "scores" in first
        assert first["relevance_score"] >= recs[-1]["relevance_score"]
        assert not any("qa event" in str(r.get("title", "")).lower() for r in recs)


def test_event_recommendations_personalization_block(client: httpx.Client) -> None:
    r = client.get(f"/v1/guest-groups/access/{CODE}/event-recommendations")
    assert r.status_code == 200
    body = r.json()
    assert "personalization" in body
    assert "stay_window" in body
    assert "total_candidates" in body
