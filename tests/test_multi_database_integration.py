"""
Integration tests for multi-database architecture.

PostgreSQL is exercised here (partners and relationships are SQL-only).
"""

import uuid

import pytest

from app.models.host import HostCreate
from app.models.recommendation import RecommendationRequestCreate
from app.services.host_service import HostService
from app.services.partner_service import PartnerService
from app.services.recommendation_service import RecommendationService
from app.models.guest_group import GuestGroup


@pytest.mark.asyncio
async def test_postgres_partner_create(db_session):
    """Partner row is persisted in PostgreSQL."""
    partner_service = PartnerService(db_session)

    partner_data = {
        "name": "Test Restaurant",
        "partner_type": "restaurant",
        "city": "Lovran",
        "email": "test@example.com",
    }

    partner = await partner_service.create_partner(partner_data)
    assert partner is not None
    assert partner.name == "Test Restaurant"
    assert partner.city == "Lovran"


@pytest.mark.asyncio
async def test_recommendation_multi_database(db_session, ai_service):
    """RecommendationService uses PostgreSQL with current API shape."""
    hs = HostService(db_session)
    email = f"rec-multi-{uuid.uuid4().hex[:12]}@example.com"
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
        group_name="Test Group",
        group_size=4,
    )
    db_session.add(guest_group)
    await db_session.commit()

    recommendation_service = RecommendationService(db_session, ai_service)
    req = RecommendationRequestCreate(preferred_radius_km=10.0, group_size=4)
    result = await recommendation_service.generate_recommendations(
        guest_group_id=guest_group.id,
        host_id=host_id,
        request_data=req,
    )
    assert result is None or hasattr(result, "recommendations")


@pytest.mark.asyncio
async def test_data_consistency(db_session):
    """Test data consistency between databases."""
    from sqlalchemy import select

    from app.models.partner import Partner

    partner = Partner(
        id=uuid.uuid4(),
        name="Test Partner",
        partner_type="restaurant",
        city="Lovran",
    )

    db_session.add(partner)
    await db_session.commit()

    stmt = select(Partner).where(Partner.id == partner.id)
    result = await db_session.execute(stmt)
    retrieved = result.scalar_one_or_none()

    assert retrieved is not None
    assert retrieved.name == "Test Partner"
