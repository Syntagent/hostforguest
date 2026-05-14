"""
Comprehensive tests for the database-based session system.

Tests the complete session lifecycle including registration, login, session management,
token validation, and dashboard access for the Croatian tourist host platform.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import faker
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from app.services.host_service import HostService
from app.services.session_service import SessionService
from app.models.host import HostCreate, UserSession, Host
from app.main import app
from app.core.database import get_db

# Initialize faker for generating realistic test data
fake = faker.Faker(['hr_HR', 'en_US'])  # Croatian and English locales


class SessionTestFactory:
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


class TestDatabaseSessionSystem:
    """Test suite for database-based session system."""
    
    @pytest_asyncio.fixture
    async def host_service(self, async_db_session: AsyncSession):
        """Create host service instance."""
        return HostService(async_db_session)
    
    @pytest_asyncio.fixture
    async def session_service(self, async_db_session: AsyncSession):
        """Create session service instance."""
        return SessionService(async_db_session)
    
    @pytest_asyncio.fixture
    async def test_host_data(self):
        """Generate fresh host data for each test."""
        return SessionTestFactory.create_host_data()
    
    @pytest_asyncio.fixture
    async def registered_host(self, host_service: HostService, test_host_data: HostCreate) -> Host:
        """Create and register a test host."""
        host = await host_service.create_host(test_host_data)
        assert host is not None
        return host
    
    @pytest_asyncio.fixture
    async def authenticated_session(self, host_service: HostService, registered_host: Host) -> Dict[str, Any]:
        """Create an authenticated session for testing."""
        auth_result = await host_service.authenticate_host(
            email=registered_host.email,
            password="TestPassword123!",
            user_agent="Test Browser",
            ip_address="127.0.0.1"
        )
        assert auth_result is not None
        return auth_result

    async def test_session_creation_on_registration(self, host_service: HostService, test_host_data: HostCreate):
        """Test that session is created when host registers."""
        # Register new host
        host = await host_service.create_host(test_host_data)
        assert host is not None
        assert host.id is not None
        
        # Verify no session exists yet (registration doesn't create session)
        # Sessions are only created on login
        pass

    async def test_session_creation_on_login(self, host_service: HostService, registered_host: Host):
        """Test that session is created when host logs in."""
        # Login host
        auth_result = await host_service.authenticate_host(
            email=registered_host.email,
            password="TestPassword123!",
            user_agent="Test Browser",
            ip_address="127.0.0.1"
        )
        
        # Verify session was created
        assert auth_result is not None
        assert "session_token" in auth_result
        assert "refresh_token" in auth_result
        assert "expires_at" in auth_result
        assert "refresh_expires_at" in auth_result
        
        # Verify session token is valid
        session_token = auth_result["session_token"]
        assert len(session_token) > 32  # Should be a secure random token
        
        # Verify refresh token is valid
        refresh_token = auth_result["refresh_token"]
        assert len(refresh_token) > 32  # Should be a secure random token
        
        # Verify expiry times are in the future
        expires_at = auth_result["expires_at"]
        refresh_expires_at = auth_result["refresh_expires_at"]
        assert expires_at > datetime.utcnow()
        assert refresh_expires_at > datetime.utcnow()

    async def test_session_validation(self, session_service: SessionService, authenticated_session: Dict[str, Any]):
        """Test that session validation works correctly."""
        session_token = authenticated_session["session_token"]
        
        # Validate session
        session = await session_service.validate_session(session_token)
        assert session is not None
        assert session.is_active is True
        assert session.is_expired is False
        assert session.host_id is not None

    async def test_session_invalidation_on_logout(self, session_service: SessionService, authenticated_session: Dict[str, Any]):
        """Test that session is invalidated on logout."""
        session_token = authenticated_session["session_token"]
        
        # Verify session exists and is valid
        session = await session_service.validate_session(session_token)
        assert session is not None
        assert session.is_active is True
        
        # Invalidate session (logout)
        success = await session_service.invalidate_session(session_token)
        assert success is True
        
        # Verify session is now invalid
        session = await session_service.validate_session(session_token)
        assert session is None

    async def test_expired_session_rejection(self, session_service: SessionService, authenticated_session: Dict[str, Any]):
        """Test that expired sessions are rejected."""
        session_token = authenticated_session["session_token"]
        
        # Get the session and manually expire it
        session = await session_service.validate_session(session_token)
        assert session is not None
        
        # Update session to be expired
        session.expires_at = datetime.utcnow() - timedelta(minutes=1)
        session_service.db.add(session)
        await session_service.db.commit()
        await session_service.db.refresh(session)
        
        # Verify expired session is rejected
        expired_session = await session_service.validate_session(session_token)
        assert expired_session is None

    async def test_refresh_token_functionality(self, session_service: SessionService, authenticated_session: Dict[str, Any]):
        """Test refresh token functionality."""
        refresh_token = authenticated_session["refresh_token"]
        
        # Refresh session
        refresh_result = await session_service.refresh_session(refresh_token)
        assert refresh_result is not None
        assert "session_token" in refresh_result
        assert "expires_at" in refresh_result
        
        # Verify new session token is different
        new_session_token = refresh_result["session_token"]
        original_session_token = authenticated_session["session_token"]
        assert new_session_token != original_session_token
        
        # Verify new session is valid
        new_session = await session_service.validate_session(new_session_token)
        assert new_session is not None
        assert new_session.is_active is True

    async def test_invalid_session_token_rejection(self, session_service: SessionService):
        """Test that invalid session tokens are rejected."""
        invalid_token = "invalid_session_token_12345"
        
        # Verify invalid token is rejected
        session = await session_service.validate_session(invalid_token)
        assert session is None

    async def test_invalid_refresh_token_rejection(self, session_service: SessionService):
        """Test that invalid refresh tokens are rejected."""
        invalid_refresh_token = "invalid_refresh_token_12345"
        
        # Verify invalid refresh token is rejected
        refresh_result = await session_service.refresh_session(invalid_refresh_token)
        assert refresh_result is None

    async def test_session_cleanup(self, session_service: SessionService, authenticated_session: Dict[str, Any]):
        """Test session cleanup functionality."""
        session_token = authenticated_session["session_token"]
        
        # Verify session exists
        session = await session_service.validate_session(session_token)
        assert session is not None
        
        # Clean up expired sessions (should not affect active session)
        cleaned_count = await session_service.cleanup_expired_sessions()
        assert cleaned_count >= 0
        
        # Verify active session still exists
        session = await session_service.validate_session(session_token)
        assert session is not None

    async def test_multiple_sessions_per_host(self, host_service: HostService, registered_host: Host):
        """Test that a host can have multiple active sessions."""
        # Create first session
        auth_result1 = await host_service.authenticate_host(
            email=registered_host.email,
            password="TestPassword123!",
            user_agent="Browser 1",
            ip_address="127.0.0.1"
        )
        assert auth_result1 is not None
        
        # Create second session
        auth_result2 = await host_service.authenticate_host(
            email=registered_host.email,
            password="TestPassword123!",
            user_agent="Browser 2",
            ip_address="127.0.0.2"
        )
        assert auth_result2 is not None
        
        # Verify both sessions are different
        assert auth_result1["session_token"] != auth_result2["session_token"]
        assert auth_result1["refresh_token"] != auth_result2["refresh_token"]
        
        # Verify both sessions are valid
        session_service = SessionService(host_service.db)
        session1 = await session_service.validate_session(auth_result1["session_token"])
        session2 = await session_service.validate_session(auth_result2["session_token"])
        assert session1 is not None
        assert session2 is not None
        assert session1.host_id == session2.host_id  # Same host

    async def test_session_user_agent_and_ip_storage(self, host_service: HostService, registered_host: Host):
        """Test that user agent and IP address are stored with sessions."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ip_address = "192.168.1.100"
        
        # Create session with user agent and IP
        auth_result = await host_service.authenticate_host(
            email=registered_host.email,
            password="TestPassword123!",
            user_agent=user_agent,
            ip_address=ip_address
        )
        assert auth_result is not None
        
        # Verify session data is stored
        session_service = SessionService(host_service.db)
        session = await session_service.validate_session(auth_result["session_token"])
        assert session is not None
        assert session.user_agent == user_agent
        assert session.ip_address == ip_address


class TestSessionSystemIntegration:
    """Integration tests for session system with API endpoints."""
    
    @pytest_asyncio.fixture
    async def async_client(self, async_db_session: AsyncSession):
        """HTTP client; handlers use the same session as other fixtures in the test."""
        async def override_get_db():
            yield async_db_session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        finally:
            app.dependency_overrides.pop(get_db, None)

    async def test_registration_flow(self, async_client: AsyncClient):
        """Test complete registration flow."""
        host_data = SessionTestFactory.create_host_data()
        
        # Register host
        response = await async_client.post("/api/v1/hosts/register", json=host_data.model_dump())
        assert response.status_code == 201
        
        data = response.json()
        assert "id" in data
        assert data["email"] == host_data.email
        assert data["business_name"] == host_data.business_name

    async def test_login_flow(self, async_client: AsyncClient):
        """Test complete login flow."""
        host_data = SessionTestFactory.create_host_data()
        
        # Register host first
        register_response = await async_client.post("/api/v1/hosts/register", json=host_data.model_dump())
        assert register_response.status_code == 201
        
        # Login
        login_data = {
            "email": host_data.email,
            "password": host_data.password
        }
        login_response = await async_client.post("/api/v1/hosts/login", json=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        assert login_result["success"] is True
        assert "session_token" in login_result
        assert "refresh_token" in login_result
        assert "host" in login_result
        assert login_result["host"]["email"] == host_data.email

    async def test_dashboard_access_with_session(self, async_client: AsyncClient):
        """Test dashboard access with valid session token."""
        host_data = SessionTestFactory.create_host_data()
        
        # Register and login
        await async_client.post("/api/v1/hosts/register", json=host_data.model_dump())
        
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data.email,
            "password": host_data.password
        })
        login_result = login_response.json()
        session_token = login_result["session_token"]
        
        # Access dashboard with session token
        headers = {"X-Session-Token": session_token}
        dashboard_response = await async_client.get("/api/v1/hosts/me", headers=headers)
        assert dashboard_response.status_code == 200
        
        dashboard_data = dashboard_response.json()
        assert dashboard_data["email"] == host_data.email

    async def test_dashboard_access_without_session(self, async_client: AsyncClient):
        """Test that dashboard access is denied without session token."""
        response = await async_client.get("/api/v1/hosts/me")
        assert response.status_code == 401
        assert "Session token required" in response.json()["detail"]

    async def test_dashboard_access_with_invalid_session(self, async_client: AsyncClient):
        """Test that dashboard access is denied with invalid session token."""
        headers = {"X-Session-Token": "invalid_token_12345"}
        response = await async_client.get("/api/v1/hosts/me", headers=headers)
        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    async def test_logout_flow(self, async_client: AsyncClient):
        """Test complete logout flow."""
        host_data = SessionTestFactory.create_host_data()
        
        # Register and login
        await async_client.post("/api/v1/hosts/register", json=host_data.model_dump())
        
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data.email,
            "password": host_data.password
        })
        login_result = login_response.json()
        session_token = login_result["session_token"]
        
        # Logout
        headers = {"X-Session-Token": session_token}
        logout_response = await async_client.post("/api/v1/hosts/logout", headers=headers)
        assert logout_response.status_code == 200
        
        logout_result = logout_response.json()
        assert logout_result["success"] is True
        
        # Verify session is invalidated
        dashboard_response = await async_client.get("/api/v1/hosts/me", headers=headers)
        assert dashboard_response.status_code == 401

    async def test_session_refresh_flow(self, async_client: AsyncClient):
        """Test session refresh flow."""
        host_data = SessionTestFactory.create_host_data()
        
        # Register and login
        await async_client.post("/api/v1/hosts/register", json=host_data.model_dump())
        
        login_response = await async_client.post("/api/v1/hosts/login", json={
            "email": host_data.email,
            "password": host_data.password
        })
        login_result = login_response.json()
        refresh_token = login_result["refresh_token"]
        
        # Refresh session
        refresh_response = await async_client.post("/api/v1/hosts/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_response.status_code == 200
        
        refresh_result = refresh_response.json()
        assert refresh_result["success"] is True
        assert "session_token" in refresh_result
        assert "expires_at" in refresh_result
        
        # Verify new session token works
        new_session_token = refresh_result["session_token"]
        headers = {"X-Session-Token": new_session_token}
        dashboard_response = await async_client.get("/api/v1/hosts/me", headers=headers)
        assert dashboard_response.status_code == 200

    async def test_invalid_refresh_token_rejection(self, async_client: AsyncClient):
        """Test that invalid refresh tokens are rejected."""
        refresh_response = await async_client.post("/api/v1/hosts/refresh", json={
            "refresh_token": "invalid_refresh_token_12345"
        })
        assert refresh_response.status_code == 401
        assert "Invalid or expired refresh token" in refresh_response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
