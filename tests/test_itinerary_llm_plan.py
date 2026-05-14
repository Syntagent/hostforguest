"""
Tests for LLM itinerary JSON parsing, validation, and schema models.
"""

import json
import uuid

import pytest

from app.models.itinerary import (
    ItinerarySuggestionRequest,
    LLMItineraryDayPlan,
    LLMItineraryPlanResult,
)
from app.services.itinerary_service import (
    _llm_plan_is_usable,
    _parse_llm_itinerary_json,
    _strip_markdown_json_fence,
)


def test_strip_markdown_json_fence():
    raw = '```json\n{"a": 1}\n```'
    assert _strip_markdown_json_fence(raw) == '{"a": 1}'


def test_parse_llm_itinerary_json_roundtrip():
    data = {
        "itinerary_title": "Coastal days",
        "itinerary_description": "Sea and towns.",
        "reasoning_summary": "Logical flow.",
        "days": [
            {
                "day_number": 1,
                "day_title": "Day one",
                "day_theme": "coast",
                "ordered_attraction_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            }
        ],
    }
    text = json.dumps(data)
    parsed = _parse_llm_itinerary_json(text)
    assert parsed is not None
    plan = LLMItineraryPlanResult.model_validate(parsed)
    assert plan.itinerary_title == "Coastal days"
    assert len(plan.days) == 1


def test_llm_plan_is_usable_requires_exact_days_and_catalog():
    a = str(uuid.uuid4())
    b = str(uuid.uuid4())
    plan = LLMItineraryPlanResult(
        itinerary_title="T",
        days=[
            LLMItineraryDayPlan(day_number=1, ordered_attraction_ids=[a]),
            LLMItineraryDayPlan(day_number=2, ordered_attraction_ids=[b]),
        ],
    )
    assert _llm_plan_is_usable(plan, 2, {a, b}, [])
    assert not _llm_plan_is_usable(plan, 3, {a, b}, [])
    assert not _llm_plan_is_usable(plan, 2, {a}, [])


def test_llm_plan_must_see_enforced():
    must = uuid.uuid4()
    other = uuid.uuid4()
    plan = LLMItineraryPlanResult(
        days=[
            LLMItineraryDayPlan(day_number=1, ordered_attraction_ids=[str(other)]),
        ],
    )
    assert not _llm_plan_is_usable(plan, 1, {str(other), str(must)}, [must])

    plan2 = LLMItineraryPlanResult(
        days=[
            LLMItineraryDayPlan(
                day_number=1,
                ordered_attraction_ids=[str(must), str(other)],
            ),
        ],
    )
    assert _llm_plan_is_usable(plan2, 1, {str(must), str(other)}, [must])


def test_itinerary_suggestion_request_defaults():
    r = ItinerarySuggestionRequest(duration_days=2)
    assert r.must_see_attractions == []
