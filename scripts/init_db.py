#!/usr/bin/env python
"""
Database initialization script for TouristGuideLocal.

Creates all database tables and populates with sample data.
"""

import asyncio
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.host import Host, HostCreate
from app.models.guest_group import GuestGroup, GuestGroupCreate
from app.models.attraction import Attraction, AttractionCreate
from app.models.itinerary import Itinerary, DayPlan, ItineraryActivity
from app.models.attraction import AttractionReview

# Import all models to ensure they're registered with SQLModel metadata
from app.models import host, guest_group, attraction, itinerary, recommendation, content_source, settings

# Import the Base from the database connection
from app.db.postgresql.connection import Base

# Also import SQLModel to ensure metadata registration
from sqlmodel import SQLModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    """Create all database tables."""
    try:
        # Create async engine using settings URL
        engine = create_async_engine(
            settings.async_postgres_url,
            echo=settings.postgres_echo,
        )
        
        # Import SQLModel to get metadata
        from sqlmodel import SQLModel
        
        # Create all tables
        async with engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database tables created successfully!")
            
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

async def seed_sample_data():
    """Add sample data for development."""
    try:
        engine = create_async_engine(
            settings.async_postgres_url,
            echo=settings.postgres_echo,
        )
        
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            # Create sample host
            host = Host(
                email="host@villa-opatija.hr",
                hashed_password="$2b$12$hashedpasswordhere",
                first_name="Ana",
                last_name="Kovačić",
                phone="+385 51 123 456",
                business_name="Villa Opatija",
                business_type="villa",
                address="Oprić 71, Lovran",
                city="Lovran",
                county="Primorsko-goranska",
                country="Croatia",
                postal_code="51450",
                latitude=45.2919,
                longitude=14.2742,
                description="Beautiful villa in Lovran with sea view and local expertise",
                languages=["hr", "en", "de"],
                is_active=True,
                is_verified=True
            )
            session.add(host)
            
            # Create sample attractions
            attractions = [
                Attraction(
                    created_by_host_id=host.id,
                    name="Lungomare Promenade",
                    description="Beautiful 12km coastal promenade from Volosko to Lovran",
                    attraction_type="nature",
                    city="Opatija",
                    region="Kvarner",
                    county="Primorsko-goranska",
                    latitude=45.3381,
                    longitude=14.3081,
                    host_personal_tip="Best enjoyed in early morning or at sunset!",
                    status="active"
                ),
                Attraction(
                    created_by_host_id=host.id,
                    name="Učka Nature Park",
                    description="Mountain nature park with hiking trails and panoramic views",
                    attraction_type="nature",
                    city="Učka",
                    region="Istria",
                    latitude=45.2919,
                    longitude=14.2742,
                    host_personal_tip="Bring warm clothes - it's much cooler at the top!",
                    status="active"
                ),
                Attraction(
                    created_by_host_id=host.id,
                    name="Lovran Old Town",
                    description="Medieval town center with St. George Church",
                    attraction_type="culture",
                    city="Lovran",
                    region="Kvarner",
                    county="Primorsko-goranska",
                    latitude=45.2919,
                    longitude=14.2742,
                    host_personal_tip="Visit during cherry blossom season in April!",
                    status="active"
                )
            ]
            
            for attraction in attractions:
                session.add(attraction)
            
            await session.commit()
            logger.info("Sample data seeded successfully!")
            
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise

async def main():
    """Main initialization function."""
    logger.info("🚀 Initializing TouristGuideLocal database...")
    
    try:
        # Test database connection first
        engine = create_async_engine(
            settings.async_postgres_url,
            echo=settings.postgres_echo,
        )
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful!")
        await engine.dispose()
        
        # Create tables
        await create_tables()
        
        # Seed sample data
        await seed_sample_data()
        
        logger.info("🎉 Database initialization complete!")
        logger.info("🔗 You can now test the API endpoints with data!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
