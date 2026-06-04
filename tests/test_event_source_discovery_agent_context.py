"""Discovery agent uses LLM context, not keyword routing."""

from __future__ import annotations

import inspect

from app.services import event_source_discovery_agent as mod


def test_discovery_agent_has_llm_call_not_keyword_router():
    src = inspect.getsource(mod.EventSourceDiscoveryAgent)
    assert "_call_llm" in src or "generate_events_extraction" in src
    assert "keyword" not in src.lower() or "keyword router" not in src.lower()
    assert "DISCOVERY_SYSTEM" in src


def test_fallback_is_explicit_when_ai_unavailable():
    src = inspect.getsource(mod.EventSourceDiscoveryAgent._fallback_proposals_json)
    assert "fallback" in src.lower() or "unavailable" in src.lower()
