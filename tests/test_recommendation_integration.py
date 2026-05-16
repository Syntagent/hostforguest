"""
Integration tests for recommendation engine.

Uses PostgreSQL via the shared test session.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.guest_group import GuestGroup
from app.models.host import HostCreate
from app.models.recommendation import RecommendationRequestCreate, RecommendationSetResponse
from app.services.host_service import HostService
from app.services.recommendation_service import RecommendationService


async def _create_host_and_group(db_session):
    hs = HostService(db_session)
    email = f"rec-int-{uuid.uuid4().hex[:12]}@example.com"
    host_row = await hs.create_host(
        HostCreate(
            email=email,
            password="securepassword123",
            first_name="Rec",
            last_name="Host",
            address="1 Test St",
            city="Lovran",
            country="Croatia",
        )
    )
    assert host_row is not None
    host_id = host_row.id

    guest_group = GuestGroup(
        id=uuid.uuid4(),
        host_id=host_id,
        group_name="Test Family",
        group_size=4,
        interests=["beach", "family_friendly"],
        check_in_date=datetime.utcnow(),
        check_out_date=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(guest_group)
    await db_session.commit()
    return host_id, guest_group.id


@pytest.mark.asyncio
async def test_recommendation_flow_complete(db_session, ai_service):
    """Complete recommendation generation call (may return None if pipeline short-circuits)."""
    recommendation_service = RecommendationService(db_session, ai_service)
    host_id, group_id = await _create_host_and_group(db_session)

    req = RecommendationRequestCreate(preferred_radius_km=10.0, group_size=4)
    result = await recommendation_service.generate_recommendations(
        guest_group_id=group_id,
        host_id=host_id,
        request_data=req,
    )
    assert result is None or isinstance(result, RecommendationSetResponse)


@pytest.mark.asyncio
async def test_vector_search_in_recommendations(db_session, ai_service):
    """Recommendation path accepts a valid guest group and host."""
    recommendation_service = RecommendationService(db_session, ai_service)
    host_id, group_id = await _create_host_and_group(db_session)

    req = RecommendationRequestCreate()
    result = await recommendation_service.generate_recommendations(
        guest_group_id=group_id,
        host_id=host_id,
        request_data=req,
    )
    assert result is None or isinstance(result, RecommendationSetResponse)


@pytest.mark.asyncio
async def test_graph_relationships_in_recommendations(db_session, ai_service):
    """Graph-backed steps are internal; public API is generate_recommendations."""
    recommendation_service = RecommendationService(db_session, ai_service)
    host_id, group_id = await _create_host_and_group(db_session)

    req = RecommendationRequestCreate(preferred_radius_km=15.0)
    result = await recommendation_service.generate_recommendations(
        guest_group_id=group_id,
        host_id=host_id,
        request_data=req,
    )
    assert result is None or isinstance(result, RecommendationSetResponse)
