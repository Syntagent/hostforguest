"""
Basic tests for the database-based session system.

Tests the core session functionality using the existing test infrastructure.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import faker
from sqlalchemy.orm import Session

from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.models.host import HostCreate, UserSession, Host
from app.models.settings import HostSettings

# Initialize faker for generating realistic test data
fake = faker.Faker(['hr_HR', 'en_US'])  # Croatian and English locales


class BasicSessionTestFactory:
    """Factory for creating session test data."""
    
    @staticmethod
    def create_host_data(**overrides) -> HostCreate:
        """Create realistic host registration data for session testing."""
        default_data = {
            "email": fake.email(),
            "password": "TestPassword123!",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": f"+385 {fake.random_int(min=10, max=99)} {fake.random_int(min=100, max=999)} {fake.random_int(min=100, max=999)}",
            "business_name": f"{fake.word().title()} Villa",
            "business_type": "villa",
            "address": fake.street_address(),
            "city": "Lovran",
            "county": "Primorsko-goranska",
            "postal_code": "51450",
            "country": "Croatia",
            "latitude": 45.2919,
            "longitude": 14.2747,
            "local_specialties": ["istrian_cuisine", "wine_tours"],
            "languages": ["hr", "en", "de"],
            "max_group_size": 8,
            "description": "Beautiful villa in Lovran with sea view",
            "welcome_message": "Welcome to our beautiful villa in Lovran!"
        }
        default_data.update(overrides)
        return HostCreate(**default_data)


class TestBasicSessionSystem:
    """Basic test suite for session system."""
    
    def test_session_token_generation(self):
        """Test that session tokens are generated correctly."""
        # Create a mock session service
        session_service = SessionService(None)  # We don't need db for token generation
        
        # Generate tokens
        session_token = session_service._generate_session_token()
        refresh_token = session_service._generate_refresh_token()
        
        # Verify tokens are generated
        assert session_token is not None
        assert refresh_token is not None
        assert len(session_token) > 32  # Should be a secure random token
        assert len(refresh_token) > 32  # Should be a secure random token
        assert session_token != refresh_token  # Should be different

    def test_host_password_hashing(self):
        """Test that host passwords are hashed correctly."""
        # Create a mock host service
        host_service = HostService(None)  # We don't need db for password hashing
        
        # Test password hashing
        password = "TestPassword123!"
        hashed_password = host_service.get_password_hash(password)
        
        # Verify password is hashed
        assert hashed_password is not None
        assert hashed_password != password  # Should be different from plain text
        assert len(hashed_password) > 20  # Should be a reasonable hash length
        
        # Verify password verification works
        assert host_service.verify_password(password, hashed_password) is True
        assert host_service.verify_password("WrongPassword", hashed_password) is False

    def test_user_session_model_properties(self):
        """Test UserSession model properties."""
        # Create a session with future expiry
        future_time = datetime.utcnow() + timedelta(hours=1)
        past_time = datetime.utcnow() - timedelta(hours=1)
        
        # Test active session
        active_session = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=future_time,
            is_active=True
        )
        
        assert active_session.is_expired is False
        assert active_session.is_active is True
        
        # Test expired session
        expired_session = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=past_time,
            is_active=True
        )
        
        assert expired_session.is_expired is True
        
        # Test refresh token expiry
        session_with_refresh = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=future_time,
            refresh_token="refresh_token",
            refresh_expires_at=future_time,
            is_active=True
        )
        
        assert session_with_refresh.is_refresh_expired is False
        
        # Test expired refresh token
        session_with_expired_refresh = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=future_time,
            refresh_token="refresh_token",
            refresh_expires_at=past_time,
            is_active=True
        )
        
        assert session_with_expired_refresh.is_refresh_expired is True

    def test_host_model_creation(self):
        """Test Host model creation."""
        # Create host data
        host_data = BasicSessionTestFactory.create_host_data()
        
        # Create host instance
        host = Host(
            email=host_data.email,
            hashed_password="hashed_password",
            first_name=host_data.first_name,
            last_name=host_data.last_name,
            phone=host_data.phone,
            business_name=host_data.business_name,
            business_type=host_data.business_type,
            address=host_data.address,
            city=host_data.city,
            county=host_data.county,
            postal_code=host_data.postal_code,
            country=host_data.country,
            latitude=host_data.latitude,
            longitude=host_data.longitude,
            local_specialties=host_data.local_specialties,
            languages=host_data.languages,
            max_group_size=host_data.max_group_size,
            description=host_data.description,
            welcome_message=host_data.welcome_message,
            is_active=True,
            is_verified=False,
            subscription_tier="basic",
            subscription_active=True
        )
        
        # Verify host properties
        assert host.email == host_data.email
        assert host.first_name == host_data.first_name
        assert host.last_name == host_data.last_name
        assert host.business_name == host_data.business_name
        assert host.city == host_data.city
        assert host.country == host_data.country
        assert host.is_active is True
        assert host.is_verified is False
        assert host.subscription_tier == "basic"
        assert host.subscription_active is True

    def test_host_settings_creation(self):
        """Test HostSettings model creation."""
        host_id = uuid.uuid4()
        
        # Create host settings
        settings = HostSettings(
            host_id=host_id,
            default_language="hr",
            supported_languages=["hr", "en", "de"],
            custom_settings={"business_hours": {"monday": "09:00-17:00", "tuesday": "09:00-17:00"}},
            preferred_ai_provider="google",
            ai_personality="friendly_local_expert"
        )
        
        # Verify settings properties
        assert settings.host_id == host_id
        assert settings.default_language == "hr"
        assert "hr" in settings.supported_languages
        assert "en" in settings.supported_languages
        assert "de" in settings.supported_languages
        assert settings.custom_settings["business_hours"]["monday"] == "09:00-17:00"
        assert settings.preferred_ai_provider == "google"
        assert settings.ai_personality == "friendly_local_expert"

    def test_session_creation_data_structure(self):
        """Test the data structure for session creation."""
        host_id = uuid.uuid4()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ip_address = "192.168.1.100"
        
        # Create session data structure
        session = UserSession(
            id=uuid.uuid4(),
            host_id=host_id,
            session_token="test_session_token_12345",
            refresh_token="test_refresh_token_12345",
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            refresh_expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        
        # Verify session data structure
        assert session.host_id == host_id
        assert session.session_token == "test_session_token_12345"
        assert session.refresh_token == "test_refresh_token_12345"
        assert session.user_agent == user_agent
        assert session.ip_address == ip_address
        assert session.is_active is True
        assert session.is_expired is False
        assert session.is_refresh_expired is False

    def test_session_invalidation_logic(self):
        """Test session invalidation logic."""
        # Create an active session
        session = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        # Verify session is active
        assert session.is_active is True
        
        # Simulate invalidation
        session.is_active = False
        
        # Verify session is now inactive
        assert session.is_active is False

    def test_session_expiry_logic(self):
        """Test session expiry logic."""
        # Create a session that expires in 1 minute
        session = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=datetime.utcnow() + timedelta(minutes=1),
            is_active=True
        )
        
        # Verify session is not expired yet
        assert session.is_expired is False
        
        # Create a session that expired 1 minute ago
        expired_session = UserSession(
            id=uuid.uuid4(),
            host_id=uuid.uuid4(),
            session_token="test_token",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            is_active=True
        )
        
        # Verify session is expired
        assert expired_session.is_expired is True

    def test_croatian_tourism_data_validation(self):
        """Test Croatian tourism data validation."""
        # Test valid Croatian data
        valid_host_data = BasicSessionTestFactory.create_host_data(
            city="Lovran",
            county="Primorsko-goranska",
            postal_code="51450",
            country="Croatia",
            latitude=45.2919,
            longitude=14.2747,
            local_specialties=["istrian_cuisine", "wine_tours"],
            languages=["hr", "en", "de"]
        )
        
        # Verify Croatian data
        assert valid_host_data.city == "Lovran"
        assert valid_host_data.county == "Primorsko-goranska"
        assert valid_host_data.postal_code == "51450"
        assert valid_host_data.country == "Croatia"
        assert valid_host_data.latitude == 45.2919
        assert valid_host_data.longitude == 14.2747
        assert "istrian_cuisine" in valid_host_data.local_specialties
        assert "hr" in valid_host_data.languages
        assert "en" in valid_host_data.languages
        assert "de" in valid_host_data.languages

    def test_session_security_features(self):
        """Test session security features."""
        # Test token uniqueness
        session_service = SessionService(None)
        
        tokens = set()
        for _ in range(100):
            token = session_service._generate_session_token()
            tokens.add(token)
        
        # Verify all tokens are unique
        assert len(tokens) == 100
        
        # Test refresh token uniqueness
        refresh_tokens = set()
        for _ in range(100):
            token = session_service._generate_refresh_token()
            refresh_tokens.add(token)
        
        # Verify all refresh tokens are unique
        assert len(refresh_tokens) == 100
        
        # Verify session and refresh tokens are different
        assert tokens.isdisjoint(refresh_tokens)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
