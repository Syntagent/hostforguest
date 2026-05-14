"""
PostgreSQL database connection manager with pgvector support.

Handles database connections, sessions, and vector operations for the Croatian tourist platform.
Falls back to SQLite for development when PostgreSQL is not available.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from sqlalchemy.engine import Connection
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try PostgreSQL first if enabled, otherwise use SQLite
if settings.use_postgresql:
    # Create the async engine for PostgreSQL (doesn't verify connectivity yet)
    engine = create_async_engine(
        settings.async_postgres_url,
        echo=settings.postgres_echo,
        future=True,
        pool_pre_ping=True,
    )
    logger.info("Configured PostgreSQL database (connectivity will be verified on init)")
    USE_POSTGRESQL = True
else:
    # Use SQLite for development
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True
    )
    logger.info("Using SQLite database (development mode)")
    USE_POSTGRESQL = False

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for SQLAlchemy models
Base = declarative_base()

# Import all models to ensure they are registered
def import_models():
    """Import all models to ensure they are registered with SQLAlchemy."""
    try:
        from app.models.settings import HostSettings, SystemSettings, APIKeyTemplate  # noqa: F401
        from app.models import channel_integration  # noqa: F401
        from app.models import maintenance  # noqa: F401
        from app.models import adaptation  # noqa: F401
        logger.info("Models imported successfully")
    except ImportError as e:
        logger.warning(f"Could not import some models: {e}")

# Import models when module loads
import_models()


def _apply_partner_booking_channel_migrations(connection: Connection, dialect: str) -> None:
    """Add OTA columns and relax nullability for existing databases (idempotent)."""
    if dialect == "postgresql":
        stmts = [
            "ALTER TABLE partner_bookings ALTER COLUMN guest_group_id DROP NOT NULL",
            "ALTER TABLE partner_bookings ALTER COLUMN partner_id DROP NOT NULL",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS source_channel VARCHAR(50)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_reservation_id VARCHAR(128)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_room_id VARCHAR(64)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_status VARCHAR(64)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_updated_at TIMESTAMP",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS local_sync_override BOOLEAN DEFAULT false",
        ]
    else:
        # SQLite: ADD COLUMN IF NOT EXISTS; nullability change via table rebuild is heavy — new DBs only
        stmts = [
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS source_channel VARCHAR(50)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_reservation_id VARCHAR(128)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_room_id VARCHAR(64)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_status VARCHAR(64)",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS external_updated_at TIMESTAMP",
            "ALTER TABLE partner_bookings ADD COLUMN IF NOT EXISTS local_sync_override BOOLEAN DEFAULT 0",
        ]
    for stmt in stmts:
        try:
            connection.execute(text(stmt))
        except Exception as e:
            logger.debug("Schema migration skipped or failed (may be expected): %s — %s", stmt, e)

    # SQLite cannot DROP NOT NULL easily; fresh create_all uses new definition
    if dialect == "postgresql":
        try:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_partner_booking_channel_external "
                    "ON partner_bookings (source_channel, external_reservation_id) "
                    "WHERE external_reservation_id IS NOT NULL AND source_channel IS NOT NULL"
                )
            )
        except Exception as e:
            logger.debug("Partial unique index creation skipped: %s", e)


async def ensure_channel_integration_schema() -> None:
    """Run lightweight DDL for channel integration on existing PostgreSQL/SQLite DBs."""

    def _run(sync_conn: Connection) -> None:
        dialect = sync_conn.dialect.name
        _apply_partner_booking_channel_migrations(sync_conn, dialect)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(_run)
        logger.info("Channel integration schema checks applied")
    except Exception as e:
        logger.warning("Channel integration schema migration non-fatal: %s", e)


def _apply_itinerary_template_migrations(connection: Connection, dialect: str) -> None:
    """Allow itinerary templates: nullable guest_group/dates, is_template flag."""
    if dialect == "postgresql":
        stmts = [
            "ALTER TABLE itineraries ALTER COLUMN guest_group_id DROP NOT NULL",
            "ALTER TABLE itineraries ALTER COLUMN start_date DROP NOT NULL",
            "ALTER TABLE itineraries ALTER COLUMN end_date DROP NOT NULL",
            "ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false",
        ]
    else:
        stmts = [
            "ALTER TABLE itineraries ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT 0",
        ]
    for stmt in stmts:
        try:
            connection.execute(text(stmt))
        except Exception as e:
            logger.debug("Itinerary template migration skipped or failed: %s — %s", stmt, e)


def _apply_partner_trade_columns(connection: Connection, dialect: str) -> None:
    """Add trade_categories / emergency_available for majstori matching (idempotent)."""
    if dialect == "postgresql":
        stmts = [
            "ALTER TABLE partners ADD COLUMN IF NOT EXISTS trade_categories JSONB DEFAULT '[]'::jsonb",
            "ALTER TABLE partners ADD COLUMN IF NOT EXISTS emergency_available BOOLEAN DEFAULT false",
        ]
    else:
        stmts = [
            "ALTER TABLE partners ADD COLUMN IF NOT EXISTS trade_categories TEXT",
            "ALTER TABLE partners ADD COLUMN IF NOT EXISTS emergency_available BOOLEAN DEFAULT 0",
        ]
    for stmt in stmts:
        try:
            connection.execute(text(stmt))
        except Exception as e:
            logger.debug("Partner trade column migration skipped: %s — %s", stmt, e)


async def ensure_partner_trade_schema() -> None:
    def _run(sync_conn: Connection) -> None:
        _apply_partner_trade_columns(sync_conn, sync_conn.dialect.name)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(_run)
        logger.info("Partner trade schema checks applied")
    except Exception as e:
        logger.warning("Partner trade schema migration non-fatal: %s", e)


async def ensure_itinerary_template_schema() -> None:
    """Apply itinerary template columns / nullability on existing DBs."""

    def _run(sync_conn: Connection) -> None:
        dialect = sync_conn.dialect.name
        _apply_itinerary_template_migrations(sync_conn, dialect)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(_run)
        logger.info("Itinerary template schema checks applied")
    except Exception as e:
        logger.warning("Itinerary template schema migration non-fatal: %s", e)




async def ensure_cleaning_partner_schema() -> None:
    """Add rate_card / price_notes on partners for cleaning fee transparency (idempotent)."""

    def _run(sync_conn) -> None:
        dialect = sync_conn.dialect.name
        if dialect == "postgresql":
            stmts = [
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS rate_card JSONB DEFAULT '{}'::jsonb",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS price_notes TEXT",
            ]
        else:
            stmts = [
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS rate_card TEXT",
                "ALTER TABLE partners ADD COLUMN IF NOT EXISTS price_notes TEXT",
            ]
        for stmt in stmts:
            try:
                sync_conn.execute(text(stmt))
            except Exception as e:
                logger.debug("Cleaning partner schema migration skipped: %s -- %s", stmt, e)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(_run)
        logger.info("Cleaning partner schema checks applied")
    except Exception as e:
        logger.warning("Cleaning partner schema migration non-fatal: %s", e)


async def ensure_guest_preference_age_category_length() -> None:
    """Widen age_category for multi-select (comma-separated keys)."""
    if not USE_POSTGRESQL:
        return
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE guest_preferences ALTER COLUMN age_category TYPE VARCHAR(200)")
            )
        logger.info("guest_preferences.age_category length ensured")
    except Exception as e:
        logger.debug("guest_preferences.age_category alter skipped: %s", e)


async def ensure_embedding_columns() -> None:
    """Add embedding columns that create_all won't add to existing tables."""
    stmts = [
        "ALTER TABLE attractions ADD COLUMN IF NOT EXISTS embedding TEXT",
        "ALTER TABLE guest_groups ADD COLUMN IF NOT EXISTS preference_embedding TEXT",
    ]
    try:
        async with engine.begin() as conn:
            for stmt in stmts:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    logger.debug("Embedding column migration skipped: %s — %s", stmt, e)
        logger.info("Embedding column checks applied")
    except Exception as e:
        logger.warning("Embedding column migration non-fatal: %s", e)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def _switch_to_sqlite() -> None:
    """Switch the global engine/session to SQLite fallback."""
    global engine, AsyncSessionLocal, USE_POSTGRESQL
    try:
        await engine.dispose()
    except Exception:
        pass
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    USE_POSTGRESQL = False
    logger.info("Switched to SQLite fallback engine")


async def init_postgresql() -> None:
    """
    Initialize database with extensions (PostgreSQL) or create tables (SQLite).
    
    Creates necessary extensions and tables.
    """
    try:
        # First verify connectivity; if Postgres is configured but unreachable, fall back to SQLite
        try:
            async with engine.begin() as conn:
                if USE_POSTGRESQL:
                    # Basic connectivity probe
                    try:
                        await conn.execute(text("SELECT 1"))
                    except Exception as e:
                        logger.warning(f"PostgreSQL not reachable, falling back to SQLite: {e}")
                        await _switch_to_sqlite()
                        # Re-open connection with SQLite and create tables
                        async with engine.begin() as sqlite_conn:
                            await sqlite_conn.run_sync(Base.metadata.create_all)
                        logger.info("Database tables created successfully (SQLite)")
                        await ensure_channel_integration_schema()
                        await ensure_itinerary_template_schema()
                        await ensure_embedding_columns()
                        await ensure_guest_preference_age_category_length()
                        await ensure_cleaning_partner_schema()
                        await ensure_partner_trade_schema()
                        return

                    # Try to enable pgvector extension (PostgreSQL only) - optional
                    try:
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                        logger.info("pgvector extension enabled")
                    except Exception as e:
                        logger.warning(f"pgvector extension not available: {e}")
                    
                    # Skip PostGIS and UUID extensions for now - they're optional
                    logger.info("Skipping optional PostGIS and UUID extensions")
                else:
                    logger.info("Using SQLite - vector operations will be simulated")
                
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info(f"Database tables created successfully ({'PostgreSQL' if USE_POSTGRESQL else 'SQLite'})")
        except Exception as e:
            # If opening the connection itself failed and Postgres was intended, fall back
            if settings.use_postgresql:
                logger.warning(f"Database engine begin failed, falling back to SQLite: {e}")
                await _switch_to_sqlite()
                async with engine.begin() as sqlite_conn:
                    await sqlite_conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully (SQLite)")
            else:
                raise
        await ensure_channel_integration_schema()
        await ensure_itinerary_template_schema()
        await ensure_embedding_columns()
        await ensure_guest_preference_age_category_length()
        await ensure_cleaning_partner_schema()
        await ensure_partner_trade_schema()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_postgresql() -> None:
    """
    Close database connections.
    """
    await engine.dispose()
    logger.info("Database connections closed")


class PostgreSQLManager:
    """
    Database manager for the Croatian tourist platform.
    Handles both PostgreSQL and SQLite fallback.
    """
    
    def __init__(self):
        self.engine = engine
        self.session_maker = AsyncSessionLocal
        self.use_postgresql = USE_POSTGRESQL
    
    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.
        
        Returns:
            AsyncSession: Database session
        """
        return AsyncSessionLocal()
    
    async def execute_vector_query(self, session: AsyncSession, query: str, params: Optional[dict] = None):
        """
        Execute a vector similarity query.
        
        Args:
            session: Database session
            query: SQL query with vector operations
            params: Query parameters
            
        Returns:
            Query result
        """
        try:
            if not self.use_postgresql:
                # Simulate vector operations for SQLite
                logger.warning("Vector query simulated for SQLite")
                return []
                
            result = await session.execute(text(query), params or {})
            return result.fetchall()
        except Exception as e:
            logger.error(f"Vector query error: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check database health.
        
        Returns:
            bool: True if database is healthy
        """
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
postgresql_manager = PostgreSQLManager() 
