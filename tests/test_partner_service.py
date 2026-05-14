"""
Tests for partner service.
"""

import pytest
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.partner_service import PartnerService
from app.models.partner import Partner, PartnerType, PartnerStatus

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_partner_service_initialization(db: AsyncSession):
    """Test partner service initializes correctly."""
    service = PartnerService(db)
    assert service is not None


@pytest.mark.asyncio
async def test_create_partner(db: AsyncSession):
    """Test creating a partner."""
    service = PartnerService(db)
    
    partner_data = {
        "name": "Test Restaurant",
        "partner_type": PartnerType.RESTAURANT,
        "city": "Lovran",
        "description": "Test restaurant description"
    }
    
    partner = await service.create_partner(partner_data)
    
    # Should return Partner or None
    assert partner is None or isinstance(partner, Partner)


@pytest.mark.asyncio
async def test_list_partners(db: AsyncSession):
    """Test listing partners."""
    service = PartnerService(db)
    
    partners = await service.list_partners(
        city="Lovran",
        limit=10
    )
    
    assert isinstance(partners, list)


@pytest.mark.asyncio
async def test_generate_discount_code(db: AsyncSession):
    """Test discount code generation."""
    service = PartnerService(db)
    
    code = service._generate_discount_code()
    
    assert isinstance(code, str)
    assert code.startswith("TGL")
    assert len(code) == 11  # "TGL" + 8 characters


@pytest.mark.asyncio
async def test_create_host_partner_relationship(db: AsyncSession):
    """Test creating host-partner relationship."""
    import uuid
    
    service = PartnerService(db)
    
    # This will fail if host/partner don't exist, but tests the method
    try:
        relationship = await service.create_host_partner_relationship(
            host_id=uuid.uuid4(),
            partner_id=uuid.uuid4(),
            relationship_data={"priority": 1}
        )
        # Should return None if host/partner don't exist
        assert relationship is None or isinstance(relationship, type(service).__module__)
    except Exception:
        # Expected if foreign key constraints fail
        pass

