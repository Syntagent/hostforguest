"""
Test guest interface functionality for TouristGuideLocal.

Tests the complete guest flow from access code entry to preference collection.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.guest_group import GuestGroup, AccessCode, GuestPreference
from app.models.host import Host
from app.services.guest_group_service import GuestGroupService


class TestGuestInterface:
    """Test guest interface functionality."""

    @pytest.fixture
    async def test_host(self, async_db_session: AsyncSession) -> Host:
        """Create a test host for guest interface testing."""
        from app.services.host_service import HostService
        from app.models.host import HostCreate
        
        host_service = HostService(async_db_session)
        host_data = HostCreate(
            email="test-host@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="Host",
            business_name="Test Villa",
            address="123 Test Street",
            city="Lovran",
            country="Croatia"
        )
        
        host_response = await host_service.create_host(host_data)
        if host_response:
            # Get the actual Host object from the database
            host = await host_service.get_host_by_id(host_response.id)
            return host
        else:
            raise Exception("Failed to create test host")

    @pytest.fixture
    async def test_guest_group(self, async_db_session: AsyncSession, test_host: Host) -> GuestGroup:
        """Create a test guest group with access code."""
        from app.models.guest_group import GuestGroupCreate
        guest_service = GuestGroupService(async_db_session)
        
        group_data = GuestGroupCreate(
            group_name="Test Family Vacation",
            group_size=4,
            lead_guest_name="Test Family",
            lead_guest_email="test@example.com",
            preferred_language="en"
        )
        
        guest_group_response = await guest_service.create_guest_group(
            host_id=test_host.id,
            group_data=group_data
        )
        
        if guest_group_response:
            # create_guest_group already issues an initial access code
            guest_group = await guest_service.get_guest_group_by_id(guest_group_response.id)
            return guest_group
        else:
            raise Exception("Failed to create test guest group")

    async def test_guest_access_code_validation(self, async_client: AsyncClient, async_db_session: AsyncSession, test_guest_group: GuestGroup):
        """Test that guests can validate access codes."""
        
        # Get the access code from the database
        from sqlalchemy import select
        from app.models.guest_group import AccessCode
        
        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()
        
        # Test access code validation
        response = await async_client.get(f"/api/v1/guest-groups/access/{access_code.code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["group_name"] == "Test Family Vacation"
        assert data["group_size"] == 4
        print("✅ Access code validation successful")

    async def test_guest_preference_creation(self, async_client: AsyncClient, async_db_session: AsyncSession, test_guest_group: GuestGroup):
        """Test that guests can create preferences."""
        
        # Get the access code
        from sqlalchemy import select
        from app.models.guest_group import AccessCode
        
        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()
        
        # Test adding guest preference
        preference_data = {
            "guest_name": "John Smith",
            "age_category": "adult",
            "personal_interests": ["history", "food", "nature"],
            "dietary_needs": ["vegetarian"],
            "cultural_interests": ["traditional_music", "local_cuisine"],
            "food_interests": ["istrian_cuisine", "local_wines"],
            "language_preference": "en",
            "mobility_notes": "Email: john@example.com\nMobility: high\nBudget: medium",
        }
        
        response = await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/preferences",
            json=preference_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["guest_name"] == "John Smith"
        assert "history" in data["personal_interests"]
        assert "vegetarian" in data["dietary_needs"]
        assert "john@example.com" in (data.get("mobility_notes") or "")
        print("✅ Guest preference creation successful")

    async def test_guest_preference_multi_age_category(self, async_client: AsyncClient, async_db_session: AsyncSession, test_guest_group: GuestGroup):
        """API accepts comma-separated age groups (multi-select onboarding)."""
        from sqlalchemy import select
        from app.models.guest_group import AccessCode

        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()

        preference_data = {
            "guest_name": "Family Mix",
            "age_category": "child,adult,senior",
            "personal_interests": [],
            "dietary_needs": [],
            "language_preference": "en",
            "cultural_interests": [],
            "food_interests": [],
        }
        response = await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/preferences",
            json=preference_data,
        )
        assert response.status_code == 201
        assert response.json()["age_category"] == "child,adult,senior"

    async def test_guest_preference_retrieval(self, async_client: AsyncClient, async_db_session: AsyncSession, test_guest_group: GuestGroup):
        """Test that guests can retrieve their preferences."""
        
        # Get the access code
        from sqlalchemy import select
        from app.models.guest_group import AccessCode
        
        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()
        
        # Add a preference first
        preference_data = {
            "guest_name": "Jane Smith",
            "age_category": "adult",
            "personal_interests": ["adventure", "photography"],
            "dietary_needs": [],
            "cultural_interests": ["historic_sites"],
            "food_interests": ["seafood"],
            "language_preference": "en"
        }
        
        await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/preferences",
            json=preference_data
        )
        
        # Test retrieving preferences
        response = await async_client.get(f"/api/v1/guest-groups/access/{access_code.code}/preferences")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(pref["guest_name"] == "Jane Smith" for pref in data)
        print("✅ Guest preference retrieval successful")

    async def test_invalid_access_code(self, async_client: AsyncClient):
        """Test that invalid access codes are properly rejected."""
        
        response = await async_client.get("/api/v1/guest-groups/access/INVALID123")
        
        assert response.status_code == 404
        print("✅ Invalid access code properly rejected")

    async def test_guest_interface_end_to_end(self, async_client: AsyncClient, async_db_session: AsyncSession, test_guest_group: GuestGroup):
        """Test the complete guest interface flow."""
        
        # Get the access code
        from sqlalchemy import select
        from app.models.guest_group import AccessCode
        
        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()
        
        # Step 1: Validate access code
        response = await async_client.get(f"/api/v1/guest-groups/access/{access_code.code}")
        assert response.status_code == 200
        group_data = response.json()
        assert group_data["group_name"] == "Test Family Vacation"
        
        # Step 2: Add guest preference
        preference_data = {
            "guest_name": "Family Vacation",
            "age_category": "adult",
            "personal_interests": ["history", "nature", "food", "relaxation"],
            "dietary_needs": ["gluten-free"],
            "cultural_interests": ["traditional_music", "local_cuisine", "historic_sites"],
            "food_interests": ["istrian_cuisine", "local_wines", "traditional_dishes"],
            "language_preference": "en"
        }
        
        response = await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/preferences",
            json=preference_data
        )
        assert response.status_code == 201
        
        # Step 3: Retrieve preferences
        response = await async_client.get(f"/api/v1/guest-groups/access/{access_code.code}/preferences")
        assert response.status_code == 200
        preferences = response.json()
        assert len(preferences) >= 1
        
        print("✅ Complete guest interface flow successful")

    async def test_guest_host_offerings_by_access_code(
        self,
        async_client: AsyncClient,
        async_db_session: AsyncSession,
        test_guest_group: GuestGroup,
    ):
        """Host offerings for guests using guest-group access code (not Host.guest_access_code)."""
        from sqlalchemy import select

        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()

        response = await async_client.get(
            f"/api/v1/guest-groups/access/{access_code.code}/host-offerings"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["valid_access"] is True
        ho = data["host_offerings"]
        assert "host_info" in ho
        assert "stay_info" in ho
        assert ho["stay_info"]["city"] == ho["location_info"]["city"] == "Lovran"
        assert "Test" in ho["host_info"]["name"] or "Host" in ho["host_info"]["name"]

    async def test_guest_host_message_by_access_code(
        self,
        async_client: AsyncClient,
        async_db_session: AsyncSession,
        test_guest_group: GuestGroup,
    ):
        """Guest can POST a message using guest-group access code."""
        from sqlalchemy import select

        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()

        response = await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/host-message",
            json={"message": "Need extra towels please", "guest_name": "Guest", "type": "general"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("response_type") == "queued_for_host"

    async def test_guest_recommendations_post_returns_batch(
        self,
        async_client: AsyncClient,
        async_db_session: AsyncSession,
        test_guest_group: GuestGroup,
    ):
        """POST /recommendations/guest/{code} must not 500; response is a batch object."""
        from sqlalchemy import select

        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()

        pref = {
            "guest_name": "Rec Test Guest",
            "age_category": "adult",
            "personal_interests": ["nature"],
            "dietary_needs": [],
            "cultural_interests": [],
            "food_interests": [],
            "language_preference": "en",
        }
        assert (await async_client.post(
            f"/api/v1/guest-groups/access/{access_code.code}/preferences",
            json=pref,
        )).status_code == 201

        response = await async_client.post(
            f"/api/v1/recommendations/guest/{access_code.code}",
            json={},
        )
        assert response.status_code == 200
        body = response.json()
        assert "recommendations" in body
        assert "total_count" in body
        assert isinstance(body["recommendations"], list)

    async def test_guest_itinerary_get_returns_200_null_when_none(
        self,
        async_client: AsyncClient,
        async_db_session: AsyncSession,
        test_guest_group: GuestGroup,
    ):
        """No shared itinerary must be 200 + JSON null (not 404) for clean guest UI loads."""
        from sqlalchemy import select

        stmt = select(AccessCode).where(AccessCode.guest_group_id == test_guest_group.id)
        result = await async_db_session.execute(stmt)
        access_code = result.scalar_one()

        response = await async_client.get(
            f"/api/v1/itineraries/guest/{access_code.code}/itinerary",
        )
        assert response.status_code == 200
        assert response.text.strip() == "null"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
