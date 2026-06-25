"""Tests for A2A Telegram orchestrator and API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.a2a.agent_card import HFG_AGENT_CARDS
from app.services.a2a.agent_wrappers import (
    BookingsAgent,
    EventsAgent,
    GuestTicketAgent,
    HostDashboardAgent,
    RecommendationsAgent,
)
from app.services.a2a.orchestrator import A2AOrchestrator


def test_hfg_agent_cards_count():
    assert len(HFG_AGENT_CARDS) == 5


def test_all_agent_wrappers_instantiable():
    for cls in (
        GuestTicketAgent,
        RecommendationsAgent,
        BookingsAgent,
        EventsAgent,
        HostDashboardAgent,
    ):
        agent = cls(None)
        assert agent.agent_id


def test_classify_intent_guest_ticket():
    o = A2AOrchestrator(None)
    assert o._classify_intent("pošalji ticket za apartman 101") == "guest-ticket-hfg"


def test_classify_intent_recommendations():
    o = A2AOrchestrator(None)
    assert o._classify_intent("preporuka Lovran") == "recommendations-hfg"


def test_classify_intent_bookings():
    o = A2AOrchestrator(None)
    assert o._classify_intent("moje rezervacije") == "bookings-hfg"


def test_classify_intent_events():
    o = A2AOrchestrator(None)
    assert o._classify_intent("događaji ovaj vikend") == "events-hfg"


def test_classify_intent_dashboard():
    o = A2AOrchestrator(None)
    assert o._classify_intent("moja pretplata") == "host-dashboard-hfg"


def test_classify_intent_default():
    o = A2AOrchestrator(None)
    assert o._classify_intent("bok") == "guest-ticket-hfg"


@pytest.mark.asyncio
async def test_a2a_agents_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/a2a/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 5
    assert len(data["agents"]) == 5
    ids = {a["id"] for a in data["agents"]}
    assert ids == set(HFG_AGENT_CARDS.keys())


@pytest.mark.asyncio
async def test_a2a_health_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/a2a/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["agents_registered"] == 5


@pytest.mark.asyncio
async def test_a2a_chat_endpoint(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/a2a/chat",
        json={"message": "događaji Lovran", "user_id": "test-user"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "events-hfg"
    assert "response" in data


@pytest.mark.asyncio
async def test_telegram_webhook_start(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/a2a/telegram-webhook",
        json={
            "message": {
                "text": "/start",
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345},
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("action") == "welcome"


@pytest.mark.asyncio
async def test_telegram_webhook_text_routes_to_orchestrator(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/a2a/telegram-webhook",
        json={
            "message": {
                "text": "pretplata",
                "from": {"id": 99999, "first_name": "Test"},
                "chat": {"id": 99999},
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("agent_id") == "host-dashboard-hfg"
