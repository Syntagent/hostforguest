"""
Tests for the host service layer.

Tests host authentication, registration, CRUD operations, and business logic
for the Croatian tourist host platform using proper fixtures and factories.
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any
import faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.host_service import HostService
from app.models.host import HostCreate, HostUpdate, HostProfileCreate
from app.models.settings import HostSettings

# Initialize faker for generating realistic test data
fake = faker.Faker(['hr_HR', 'en_US'])  # Croatian and English locales


class HostFactory:
    """Factory for creating host test data with realistic values."""
    
    @staticmethod
    def create_host_data(**overrides) -> HostCreate:
        """Create realistic host registration data."""
        default_data = {
            "email": fake.email(),
            "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": f"+385 {fake.random_int(min=10, max=99)} {fake.random_int(min=100, max=999)} {fake.random_int(min=100, max=999)}",
            "business_name": f"{fake.word().title()} {fake.random_element(['Villa', 'Apartment', 'House', 'Rooms'])}",
            "business_type": fake.random_element(["apartment", "villa", "hotel", "guesthouse"]),
            "address": fake.street_address(),
            "city": fake.random_element(["Lovran", "Opatija", "Rijeka", "Pula", "Rovinj"]),
            "county": fake.random_element(["Primorsko-goranska", "Istarska"]),
            "postal_code": str(fake.random_int(min=10000, max=99999)),
            "country": "Croatia",
            "latitude": fake.pyfloat(left_digits=2, right_digits=4, min_value=42.0, max_value=46.0),
            "longitude": fake.pyfloat(left_digits=2, right_digits=4, min_value=13.0, max_value=19.0),
            "local_specialties": fake.random_elements(
                ["istrian_cuisine", "wine_tours", "hiking", "seafood", "festivals", "history"], 
                length=fake.random_int(min=1, max=4)
            ),
            "languages": fake.random_elements(["hr", "en", "de", "it", "fr"], length=fake.random_int(min=2, max=4)),
            "max_group_size": fake.random_int(min=2, max=20),
            "description": fake.text(max_nb_chars=200),
            "welcome_message": fake.text(max_nb_chars=150)
        }
        default_data.update(overrides)
        return HostCreate(**default_data)
    
    @staticmethod
    def create_profile_data(**overrides) -> HostProfileCreate:
        """Create realistic host profile data."""
        default_data = {
            "property_type": fake.random_element(["apartment", "villa", "house", "room"]),
            "number_of_rooms": fake.random_int(min=1, max=10),
            "max_guests": fake.random_int(min=2, max=15),
            "services_offered": fake.random_elements(
                ["airport_pickup", "grocery_shopping", "tour_guide", "restaurant_reservations", "laundry"], 
                length=fake.random_int(min=1, max=3)
            ),
            "amenities": fake.random_elements(
                ["wifi", "parking", "kitchen", "sea_view", "garden", "pool", "air_conditioning"], 
                length=fake.random_int(min=2, max=5)
            ),
            "expertise_areas": fake.random_elements(
                ["local_cuisine", "hidden_beaches", "hiking_trails", "wine_tasting", "historic_sites"], 
                length=fake.random_int(min=1, max=3)
            ),
            "favorite_local_spots": [
                {
                    "name": fake.company(),
                    "type": fake.random_element(["restaurant", "beach", "attraction", "nature"]),
                    "description": fake.sentence(),
                    "distance_km": fake.pyfloat(left_digits=1, right_digits=1, min_value=0.1, max_value=50.0)
                }
                for _ in range(fake.random_int(min=1, max=3))
            ]
        }
        default_data.update(overrides)
        return HostProfileCreate(**default_data)


class TestHostService:
    """Test suite for HostService."""
    
    @pytest.fixture
    def host_service(self, db_session: AsyncSession):
        """Create host service instance."""
        return HostService(db_session)
    
    @pytest.fixture
    def host_data(self):
        """Generate fresh host data for each test."""
        return HostFactory.create_host_data()
    
    @pytest.fixture
    def profile_data(self):
        """Generate fresh profile data for each test."""
        return HostFactory.create_profile_data()
    
    @pytest.fixture
    async def created_host(self, host_service: HostService, host_data: HostCreate):
        """Create a host and return the created instance."""
        return await host_service.create_host(host_data)
    
    # Host Creation Tests
    async def test_create_host_success(self, host_service: HostService, host_data: HostCreate):
        """Test successful host creation with valid data."""
        # Act
        created_host = await host_service.create_host(host_data)
        
        # Assert
        assert created_host is not None
        assert created_host.email == host_data.email
        assert created_host.first_name == host_data.first_name
        assert created_host.last_name == host_data.last_name
        assert created_host.city == host_data.city
        assert created_host.country == host_data.country
        assert created_host.is_active is True
        assert created_host.is_verified is False
        assert created_host.subscription_tier == "basic"
        assert created_host.total_guest_groups == 0
        assert created_host.average_rating == 0.0
        assert isinstance(created_host.id, uuid.UUID)
        
        # Verify host can be retrieved
        retrieved_host = await host_service.get_host_by_id(created_host.id)
        assert retrieved_host is not None
    
    async def test_create_host_duplicate_email_fails(self, host_service: HostService, host_data: HostCreate):
        """Test that creating a host with duplicate email fails."""
        # Arrange - create first host
        first_host = await host_service.create_host(host_data)
        assert first_host is not None
        
        # Act - try to create another host with same email
        duplicate_host_data = HostFactory.create_host_data(email=host_data.email)
        duplicate_host = await host_service.create_host(duplicate_host_data)
        
        # Assert
        assert duplicate_host is None
    
    @pytest.mark.parametrize("invalid_field,invalid_value", [
        ("email", "not-an-email"),
        ("max_group_size", -1),
        ("max_group_size", 0),
    ])
    async def test_create_host_invalid_data(self, host_service: HostService, invalid_field: str, invalid_value: Any):
        """Test host creation with various invalid data scenarios."""
        # Arrange
        host_data = HostFactory.create_host_data(**{invalid_field: invalid_value})
        
        # Act & Assert - This should be caught at the Pydantic validation level
        with pytest.raises(ValueError):
            await host_service.create_host(host_data)
    
    # Authentication Tests
    async def test_authenticate_host_success(self, host_service: HostService, host_data: HostCreate, created_host):
        """Test successful host authentication."""
        # Act
        authenticated_host = await host_service.authenticate_host(
            host_data.email, 
            host_data.password
        )
        
        # Assert
        assert authenticated_host is not None
        assert authenticated_host.email == host_data.email
        assert authenticated_host.id == created_host.id
    
    async def test_authenticate_host_invalid_email(self, host_service: HostService):
        """Test authentication with non-existent email."""
        # Act
        authenticated_host = await host_service.authenticate_host(
            fake.email(), 
            fake.password()
        )
        
        # Assert
        assert authenticated_host is None
    
    async def test_authenticate_host_invalid_password(self, host_service: HostService, host_data: HostCreate, created_host):
        """Test authentication with wrong password."""
        # Act
        authenticated_host = await host_service.authenticate_host(
            host_data.email, 
            fake.password()  # Wrong password
        )
        
        # Assert
        assert authenticated_host is None
    
    # CRUD Operations Tests
    async def test_get_host_by_id_success(self, host_service: HostService, created_host):
        """Test retrieving host by ID."""
        # Act
        retrieved_host = await host_service.get_host_by_id(created_host.id)
        
        # Assert
        assert retrieved_host is not None
        assert retrieved_host.id == created_host.id
        assert retrieved_host.email == created_host.email
    
    async def test_get_host_by_id_not_found(self, host_service: HostService):
        """Test retrieving non-existent host by ID."""
        # Act
        retrieved_host = await host_service.get_host_by_id(uuid.uuid4())
        
        # Assert
        assert retrieved_host is None
    
    async def test_get_host_by_email_success(self, host_service: HostService, host_data: HostCreate, created_host):
        """Test retrieving host by email."""
        # Act
        retrieved_host = await host_service.get_host_by_email(host_data.email)
        
        # Assert
        assert retrieved_host is not None
        assert retrieved_host.email == host_data.email
        assert retrieved_host.id == created_host.id
    
    async def test_update_host_success(self, host_service: HostService, created_host):
        """Test updating host information."""
        # Arrange
        new_first_name = fake.first_name()
        new_description = fake.text(max_nb_chars=200)
        new_max_group_size = fake.random_int(min=5, max=15)
        
        update_data = HostUpdate(
            first_name=new_first_name,
            description=new_description,
            max_group_size=new_max_group_size
        )
        
        # Act
        updated_host = await host_service.update_host(created_host.id, update_data)
        
        # Assert
        assert updated_host is not None
        assert updated_host.first_name == new_first_name
        assert updated_host.description == new_description
        assert updated_host.max_group_size == new_max_group_size
        assert updated_host.last_name == created_host.last_name  # Unchanged
        assert updated_host.email == created_host.email  # Unchanged
    
    async def test_update_host_not_found(self, host_service: HostService):
        """Test updating non-existent host."""
        # Act
        update_data = HostUpdate(first_name=fake.first_name())
        updated_host = await host_service.update_host(uuid.uuid4(), update_data)
        
        # Assert
        assert updated_host is None
    
    async def test_delete_host_success(self, host_service: HostService, created_host):
        """Test soft deletion of host."""
        # Act
        success = await host_service.delete_host(created_host.id)
        
        # Assert
        assert success is True
        
        # Verify host is no longer retrievable (soft deleted)
        retrieved_host = await host_service.get_host_by_id(created_host.id)
        assert retrieved_host is None
    
    async def test_delete_host_not_found(self, host_service: HostService):
        """Test deleting non-existent host."""
        # Act
        success = await host_service.delete_host(uuid.uuid4())
        
        # Assert
        assert success is False
    
    # List and Search Tests
    async def test_list_hosts_with_pagination(self, host_service: HostService):
        """Test listing hosts with pagination."""
        # Arrange - create multiple hosts
        num_hosts = 5
        created_hosts = []
        for _ in range(num_hosts):
            host_data = HostFactory.create_host_data()
            created_host = await host_service.create_host(host_data)
            assert created_host is not None
            created_hosts.append(created_host)
        
        # Act
        hosts_page1 = await host_service.list_hosts(skip=0, limit=3)
        hosts_page2 = await host_service.list_hosts(skip=3, limit=3)
        
        # Assert
        assert len(hosts_page1) == 3
        assert len(hosts_page2) == 2  # Remaining hosts
        assert all(host.is_active for host in hosts_page1 + hosts_page2)
        
        # Verify no duplicates between pages
        page1_ids = {host.id for host in hosts_page1}
        page2_ids = {host.id for host in hosts_page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_search_hosts_by_location(self, host_service: HostService):
        """Test searching hosts by city."""
        # Arrange - create hosts in specific cities
        test_city = "TestCity"
        other_city = "OtherCity"
        
        # Create hosts in test city
        test_city_hosts = []
        for _ in range(2):
            host_data = HostFactory.create_host_data(city=test_city)
            created_host = await host_service.create_host(host_data)
            assert created_host is not None
            test_city_hosts.append(created_host)
        
        # Create host in other city
        other_host_data = HostFactory.create_host_data(city=other_city)
        other_host = await host_service.create_host(other_host_data)
        assert other_host is not None
        
        # Act
        found_hosts = await host_service.search_hosts_by_location(test_city)
        
        # Assert
        assert len(found_hosts) == 2
        assert all(host.city == test_city for host in found_hosts)
        assert all(host.id in [h.id for h in test_city_hosts] for host in found_hosts)
    
    # Profile Tests
    async def test_create_host_profile_success(self, host_service: HostService, created_host, profile_data: HostProfileCreate):
        """Test creating host profile."""
        # Act
        profile = await host_service.create_host_profile(created_host.id, profile_data)
        
        # Assert
        assert profile is not None
        assert profile.host_id == created_host.id
        assert profile.property_type == profile_data.property_type
        assert profile.number_of_rooms == profile_data.number_of_rooms
        assert profile.max_guests == profile_data.max_guests
        assert set(profile.amenities) == set(profile_data.amenities)
        assert len(profile.favorite_local_spots) == len(profile_data.favorite_local_spots)
    
    async def test_create_host_profile_duplicate_fails(self, host_service: HostService, created_host, profile_data: HostProfileCreate):
        """Test that creating duplicate host profile fails."""
        # Arrange - create first profile
        first_profile = await host_service.create_host_profile(created_host.id, profile_data)
        assert first_profile is not None
        
        # Act - try to create another profile for same host
        duplicate_profile_data = HostFactory.create_profile_data()
        duplicate_profile = await host_service.create_host_profile(created_host.id, duplicate_profile_data)
        
        # Assert
        assert duplicate_profile is None
    
    async def test_get_host_profile_success(self, host_service: HostService, created_host, profile_data: HostProfileCreate):
        """Test retrieving host profile."""
        # Arrange
        created_profile = await host_service.create_host_profile(created_host.id, profile_data)
        assert created_profile is not None
        
        # Act
        retrieved_profile = await host_service.get_host_profile(created_host.id)
        
        # Assert
        assert retrieved_profile is not None
        assert retrieved_profile.host_id == created_host.id
        assert retrieved_profile.id == created_profile.id
    
    async def test_get_host_profile_not_found(self, host_service: HostService, created_host):
        """Test retrieving non-existent host profile."""
        # Act
        retrieved_profile = await host_service.get_host_profile(created_host.id)
        
        # Assert
        assert retrieved_profile is None
    
    # Utility Function Tests
    def test_password_hashing_and_verification(self, host_service: HostService):
        """Test password hashing and verification utilities."""
        # Arrange
        plain_password = fake.password(length=12)
        
        # Act
        hashed = host_service.get_password_hash(plain_password)
        is_valid = host_service.verify_password(plain_password, hashed)
        is_invalid = host_service.verify_password(fake.password(), hashed)
        
        # Assert
        assert hashed != plain_password
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert is_valid is True
        assert is_invalid is False
    
    def test_create_access_token(self, host_service: HostService):
        """Test JWT token creation."""
        # Arrange
        test_email = fake.email()
        test_data = {"sub": test_email, "role": "host"}
        
        # Act
        token = host_service.create_access_token(test_data)
        
        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long strings
        assert "." in token  # JWT format includes dots
    
    async def test_update_last_login(self, host_service: HostService, created_host):
        """Test updating last login timestamp."""
        # Arrange
        original_login = created_host.last_login
        
        # Act
        await host_service.update_last_login(created_host.id)
        
        # Assert
        updated_host = await host_service.get_host_by_id(created_host.id)
        assert updated_host is not None
        assert updated_host.last_login is not None
        assert updated_host.last_login != original_login
        # Verify timestamp is recent (within last minute)
        time_diff = datetime.utcnow() - updated_host.last_login
        assert time_diff.total_seconds() < 60 