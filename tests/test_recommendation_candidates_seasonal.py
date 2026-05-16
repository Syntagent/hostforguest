"""
Seasonal filtering in traditional candidate fetch must work on SQLite (tests) and Postgres.

Previously used JSON.contains() which compiled to invalid ``json LIKE`` on PostgreSQL.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attraction import Attraction, AttractionStatus
from app.models.guest_group import GuestGroup
from app.models.host import Host
from app.models.recommendation import RecommendationRequest, RecommendationType
from app.services.ai_service import AIService
from app.services.recommendation_candidates import RecommendationCandidates
from app.services.vector_service import VectorService


@pytest.mark.asyncio
async def test_traditional_candidates_season_filter_in_memory_sqlite(
    db_session: AsyncSession,
):
    """Seasonal branch runs without PostgreSQL-only JSON operators."""
    host = Host(
        id=uuid.uuid4(),
        email="season-cand@example.com",
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
    )
    db_session.add(gg)
    await db_session.flush()

    common = dict(
        created_by_host_id=host.id,
        description="d",
        attraction_type="cultural",
        city="Lovran",
        status=AttractionStatus.APPROVED,
    )
    a_year = Attraction(
        id=uuid.uuid4(),
        name="Year round",
        seasonal_availability="year_round",
        best_months=[],
        **common,
    )
    a_spring = Attraction(
        id=uuid.uuid4(),
        name="Spring only",
        seasonal_availability="spring",
        best_months=[3, 4, 5],
        **common,
    )
    a_winter = Attraction(
        id=uuid.uuid4(),
        name="Winter only",
        seasonal_availability="winter",
        best_months=[12, 1],
        **common,
    )
    db_session.add_all([a_year, a_spring, a_winter])
    await db_session.commit()

    req = RecommendationRequest(
        id=uuid.uuid4(),
        guest_group_id=gg.id,
        host_id=host.id,
        request_type=RecommendationType.ATTRACTION,
        season="spring",
        current_location=None,
    )
    ai = AIService()
    svc = RecommendationCandidates(db_session, VectorService(db_session, ai))
    guest_group: dict = {"group": None}
    out = await svc.get_candidate_attractions_traditional(req, guest_group, host)
    names = {x.name for x in out}
    assert "Year round" in names
    assert "Spring only" in names
    assert "Winter only" not in names
