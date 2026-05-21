"""
Pytest configuration and fixtures for TouristGuideLocal tests.

Default: in-memory SQLite (fast CI). Set ``RUN_POSTGRES_TESTS=1`` to exercise
compose Postgres on ``localhost:5434`` (see ``scripts/run-postgres-regression.sh``).
"""

import os

_RUN_POSTGRES_TESTS = os.getenv("RUN_POSTGRES_TESTS", "").lower() in ("1", "true", "yes")

# Prevent app lifespan from opening real Postgres; tests use fixture-managed DB.
if not _RUN_POSTGRES_TESTS:
    os.environ.setdefault("TOURISTGUIDE_PYTEST", "1")
else:
    os.environ["TOURISTGUIDE_PYTEST"] = "1"
    # Host-side regression: compose publishes 5434; .env may still say POSTGRES_SERVER=postgres.
    os.environ.setdefault("POSTGRES_SERVER", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5434")

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.services.settings_service import SettingsService
from app.models.host import Host
from app.models.attraction import Attraction
from app.models.guest_group import GuestGroup


if _RUN_POSTGRES_TESTS:
    from app.core.config import settings

    test_engine = create_async_engine(
        settings.async_postgres_url,
        echo=False,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
else:
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

if _RUN_POSTGRES_TESTS:
    # Single engine for fixtures and TestClient routes (avoids split-brain on one DB).
    import app.db.postgresql.connection as _pg

    _pg.engine = test_engine
    _pg.AsyncSessionLocal = TestSessionLocal
    _pg.USE_POSTGRESQL = True


def _register_models_for_sqlite_metadata() -> None:
    """Ensure ORM tables are on Base.metadata before create_all."""
    import app.models.host  # noqa: F401
    import app.models.partner  # noqa: F401
    import app.models.guest_group  # noqa: F401
    import app.models.attraction  # noqa: F401
    import app.models.recommendation  # noqa: F401
    import app.models.itinerary  # noqa: F401
    import app.models.settings  # noqa: F401
    import app.models.channel_integration  # noqa: F401
    import app.models.maintenance  # noqa: F401
    import app.models.adaptation  # noqa: F401
    import app.models.content_source  # noqa: F401
    import app.models.subscription  # noqa: F401


_integration_full_db_initialized = False


async def _recreate_all_tables() -> None:
    from app.db.postgresql.connection import (
        Base,
        ensure_attraction_host_contributions_schema,
    )

    from sqlalchemy import text

    _register_models_for_sqlite_metadata()
    async with test_engine.begin() as conn:
        if _RUN_POSTGRES_TESTS:
            await conn.execute(
                text("DROP TABLE IF EXISTS attraction_host_contributions CASCADE")
            )
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await ensure_attraction_host_contributions_schema()


@pytest_asyncio.fixture(autouse=True)
async def _reset_test_db_schema(request: pytest.FixtureRequest) -> AsyncGenerator[None, None]:
    """
    Recreate schema each test so async HTTP clients see the same DB as fixtures.
    Uses SQLite in-memory by default, or compose Postgres when RUN_POSTGRES_TESTS=1.

    ``test_integration_full`` resets once per module so class-scoped workflow state persists.
    """
    global _integration_full_db_initialized

    mod = getattr(request.node, "module", None)
    mod_name = getattr(mod, "__name__", "") or ""
    if mod_name.endswith("test_integration_full"):
        if _integration_full_db_initialized:
            yield
            return
        _integration_full_db_initialized = True
        await _recreate_all_tables()
        yield
        return

    await _recreate_all_tables()
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# Aliases used by some test files
async_db_session = db_session
db = db_session


async def create_test_host_async(db_session: AsyncSession, email: str) -> Host:
    """Create a host for async HTTP tests using the shared test DB session."""
    from app.services.host_service import HostService
    from app.models.host import HostCreate

    svc = HostService(db_session)
    created = await svc.create_host(
        HostCreate(
            email=email,
            password="testpassword123",
            first_name="Test",
            last_name="Host",
            business_name="Test Biz",
            address="1 St",
            city="Lovran",
            country="Croatia",
        )
    )
    if not created:
        raise RuntimeError(f"Failed to create host {email}")
    host = await svc.get_host_by_id(created.id)
    assert host is not None
    return host


@pytest.fixture
def client():
    """Create a synchronous test client."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client; routes DB through the same test_engine as db_session."""
    from app.main import app
    from app.core.database import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=True
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def host_token_headers(async_client: AsyncClient) -> dict[str, str]:
    """Register a unique host via HTTP and return ``X-Session-Token`` headers."""
    email = f"fixture-host-{uuid.uuid4().hex[:16]}@example.com"
    reg = {
        "email": email,
        "password": "securepassword123",
        "first_name": "Fixture",
        "last_name": "Host",
        "phone": "+38551111222",
        "business_name": "Fixture Biz",
        "business_type": "apartment",
        "address": "1 Test St",
        "city": "Lovran",
        "county": "Primorsko-goranska",
        "postal_code": "51450",
        "country": "Croatia",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "local_specialties": ["seafood"],
        "languages": ["hr", "en"],
        "max_group_size": 6,
        "description": "Fixture",
        "welcome_message": "Hi",
    }
    r = await async_client.post("/api/v1/hosts/register", json=reg)
    assert r.status_code == 201, r.text
    login = await async_client.post(
        "/api/v1/hosts/login",
        json={"email": email, "password": "securepassword123"},
    )
    assert login.status_code == 200, login.text
    return {"X-Session-Token": login.json()["session_token"]}


@pytest_asyncio.fixture
async def ai_service(db_session):
    """Create AI service for testing."""
    from app.services.ai_service import AIService

    settings_service = SettingsService(db_session)
    return AIService(settings_service)


@pytest_asyncio.fixture
async def test_host(db_session: AsyncSession) -> Host:
    """Host with password testpassword123 for login / JWT tests (e.g. attractions CRUD)."""
    from app.services.host_service import HostService
    from app.models.host import HostCreate

    svc = HostService(db_session)
    host_data = HostCreate(
        email="attractions-crud@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="Host",
        business_name="Test Villa",
        address="123 Test Street",
        city="Lovran",
        country="Croatia",
    )
    created = await svc.create_host(host_data)
    if not created:
        raise RuntimeError("Failed to create test host")
    host = await svc.get_host_by_id(created.id)
    assert host is not None
    return host


@pytest_asyncio.fixture
async def test_attraction(db_session: AsyncSession, test_host: Host) -> Attraction:
    """Single attraction owned by test_host."""
    attraction = Attraction(
        id=uuid.uuid4(),
        name="Fixture Attraction",
        description="Test attraction for CRUD tests",
        created_by_host_id=test_host.id,
        city="Lovran",
        attraction_type="cultural",
    )
    db_session.add(attraction)
    await db_session.commit()
    await db_session.refresh(attraction)
    return attraction


@pytest_asyncio.fixture
async def sample_host(db_session):
    """Create a sample host for testing."""
    host = Host(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        first_name="Test",
        last_name="Host",
        address="1 Fixture St",
        city="Lovran",
        business_type="apartment"
    )
    
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)
    
    return host


@pytest_asyncio.fixture
async def sample_attractions(db_session, sample_host):
    """Create sample attractions for testing."""
    attractions = []
    
    for i in range(5):
        attraction = Attraction(
            id=uuid.uuid4(),
            name=f"Test Attraction {i+1}",
            description=f"Description for attraction {i+1}",
            created_by_host_id=sample_host.id,
            city="Lovran",
            attraction_type="beach" if i % 2 == 0 else "cultural"
        )
        db_session.add(attraction)
        attractions.append(attraction)
    
    await db_session.commit()
    
    for attraction in attractions:
        await db_session.refresh(attraction)
    
    return attractions


@pytest_asyncio.fixture
async def sample_guest_group(db_session, sample_host):
    """Create a sample guest group for testing."""
    guest_group = GuestGroup(
        id=uuid.uuid4(),
        host_id=sample_host.id,
        group_name="Test Family",
        group_size=4,
        interests=["beach", "family_friendly"],
        check_in_date=datetime.utcnow().date(),
        check_out_date=(datetime.utcnow() + timedelta(days=7)).date()
    )
    
    db_session.add(guest_group)
    await db_session.commit()
    await db_session.refresh(guest_group)
    
    return guest_group
