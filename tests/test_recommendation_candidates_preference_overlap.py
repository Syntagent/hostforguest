"""Guest interest overlap ranks host attractions without a graph database."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import Attraction, AttractionStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.services.ai_service import AIService
from app.services.recommendation_candidates import RecommendationCandidates
from app.services.vector_service import VectorService


@pytest.mark.asyncio
async def test_preference_overlap_ranks_matching_attractions(db_session: AsyncSession):
    host = Host(
        id=uuid.uuid4(),
        email="overlap@example.com",
        hashed_password="hashed",
        first_name="Test",
        last_name="Host",
        address="1 Test St",
        city="Lovran",
    )
    db_session.add(host)
    await db_session.flush()

    gg = GuestGroup(
        id=uuid.uuid4(),
        host_id=host.id,
        group_name="Guests",
        group_size=2,
        interests=["nature", "hiking"],
        interested_regions=[],
    )
    db_session.add(gg)
    await db_session.flush()

    common = dict(
        created_by_host_id=host.id,
        description="A nice place",
        city="Lovran",
        status=AttractionStatus.APPROVED,
    )
    match = Attraction(
        id=uuid.uuid4(),
        name="Forest trail",
        attraction_type="nature",
        category_tags=["hiking", "outdoor"],
        **common,
    )
    other = Attraction(
        id=uuid.uuid4(),
        name="City museum",
        attraction_type="cultural",
        category_tags=["indoor"],
        **common,
    )
    db_session.add_all([match, other])
    await db_session.commit()

    svc = RecommendationCandidates(
        db_session, VectorService(db_session, AIService())
    )
    recs = await svc._preference_overlap_recommendations(gg.id, host, limit=10)
    ids = [r["id"] for r in recs]
    assert str(match.id) in ids
    assert str(other.id) not in ids
    assert recs[0]["matching_interests"] >= 1


@pytest.mark.asyncio
async def test_preference_overlap_empty_without_interests(db_session: AsyncSession):
    host = Host(
        id=uuid.uuid4(),
        email="no-interests@example.com",
        hashed_password="hashed",
        first_name="Test",
        last_name="Host",
        address="1 Test St",
        city="Lovran",
    )
    db_session.add(host)
    await db_session.flush()

    gg = GuestGroup(
        id=uuid.uuid4(),
        host_id=host.id,
        group_name="Guests",
        group_size=2,
        interests=[],
        interested_regions=[],
    )
    db_session.add(gg)
    await db_session.commit()

    svc = RecommendationCandidates(
        db_session, VectorService(db_session, AIService())
    )
    recs = await svc._preference_overlap_recommendations(gg.id, host, limit=10)
    assert recs == []
