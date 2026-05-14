#!/usr/bin/env python
"""
Simple table creation script for TouristGuideLocal.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

# Import all model classes to register them with SQLModel
from app.models.host import Host
from app.models.guest_group import GuestGroup  
from app.models.attraction import Attraction, AttractionReview
from app.models.itinerary import Itinerary, DayPlan, ItineraryActivity
from app.models.recommendation import Recommendation, RecommendationRequest, RecommendationSet
from app.models.content_source import ContentSource
from app.models.settings import HostSettings

from sqlmodel import SQLModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Create all database tables."""
    try:
        logger.info("🚀 Creating database tables...")
        
        # Create async engine
        engine = create_async_engine(
            settings.async_postgres_url,
            echo=settings.postgres_echo,
        )
        
        # Create all tables
        async with engine.begin() as conn:
            logger.info("Creating all tables...")
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("✅ All tables created successfully!")
            
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
