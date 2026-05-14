"""
Seed data for TouristGuideLocal database.

Creates the first host profile for the pilot location:
Apartment at Oprić 71, Lovran 51450, Croatia
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.services.host_service import HostService
from app.models.host import HostCreate, HostProfileCreate

logger = logging.getLogger(__name__)


async def create_first_host():
    """
    Create the first host profile for the Lovran pilot.
    
    This represents the apartment at Oprić 71, Lovran 51450
    as the initial host for the Croatian tourist platform.
    """
    
    # First host data - Oprić 71, Lovran
    first_host_data = HostCreate(
        email="host@opric71lovran.com",
        password="LovranHost2024!",
        first_name="Ana",
        last_name="Marić",
        phone="+385 51 291 234",
        business_name="Apartment Oprić 71",
        business_type="apartment",
        address="Oprić 71",
        city="Lovran",
        county="Primorsko-goranska",
        postal_code="51450",
        country="Croatia",
        latitude=45.2919,
        longitude=14.2742,
        local_specialties=[
            "istrian_cuisine",
            "wine_tours", 
            "hiking_trails",
            "seafood_restaurants",
            "local_festivals"
        ],
        languages=["hr", "en", "de", "it"],
        max_group_size=6,
        description="Beautiful apartment in the heart of Lovran, just steps from the sea. "
                   "Perfect base for exploring Istria's hidden gems, local cuisine, and "
                   "natural beauty. Your hosts Ana knows all the secret spots that only "
                   "locals know about.",
        welcome_message="Dobrodošli u Lovran! Welcome to our beautiful apartment! "
                       "I'm Ana, your local host, and I'm excited to help you discover "
                       "the magic of Lovran and Istria. From hidden beaches to the best "
                       "konobas, I'll make sure you experience authentic Croatian hospitality."
    )
    
    # Extended profile data
    profile_data = HostProfileCreate(
        property_type="apartment",
        number_of_rooms=2,
        max_guests=6,
        services_offered=[
            "airport_pickup",
            "grocery_shopping", 
            "local_guide_tours",
            "restaurant_reservations",
            "activity_booking",
            "luggage_storage"
        ],
        amenities=[
            "wifi",
            "parking",
            "kitchen",
            "balcony_sea_view",
            "air_conditioning",
            "washing_machine",
            "dishwasher",
            "coffee_machine"
        ],
        expertise_areas=[
            "istrian_wines",
            "hidden_beaches",
            "hiking_trails",
            "local_festivals",
            "traditional_cuisine",
            "historic_sites",
            "nature_photography",
            "seasonal_activities"
        ],
        favorite_local_spots=[
            {
                "name": "Lungomare Promenade",
                "type": "attraction",
                "description": "12km coastal walk from Opatija to Lovran with stunning sea views",
                "distance_km": 0.2,
                "best_time": "early_morning_sunset",
                "difficulty": "easy",
                "local_tip": "Start early morning for best photos and fewer crowds"
            },
            {
                "name": "Učka Nature Park",
                "type": "nature",
                "description": "Mountain hiking with panoramic views of Istria and islands",
                "distance_km": 15,
                "best_time": "spring_autumn",
                "difficulty": "moderate_challenging",
                "local_tip": "Take Vela Učka trail for the best 360-degree views"
            },
            {
                "name": "Konoba Draga",
                "type": "restaurant",
                "description": "Family-owned konoba with authentic Istrian dishes",
                "distance_km": 1.5,
                "specialty": "truffle_pasta_fresh_fish",
                "price_range": "moderate",
                "local_tip": "Ask for their daily catch and homemade fuži pasta"
            },
            {
                "name": "Medveja Beach",
                "type": "beach",
                "description": "Beautiful pebble beach with crystal clear water",
                "distance_km": 3,
                "facilities": "restaurant_parking_showers",
                "best_time": "morning_late_afternoon",
                "local_tip": "Less crowded than Lovran beach, perfect for families"
            },
            {
                "name": "Lovran Old Town",
                "type": "historic",
                "description": "Medieval town center with St. George Church and city walls",
                "distance_km": 0.3,
                "highlights": "church_bell_tower_old_walls",
                "best_time": "early_evening",
                "local_tip": "Climb the bell tower for sunset views over Kvarner Bay"
            },
            {
                "name": "Kozlović Winery",
                "type": "winery",
                "description": "Premium Istrian winery with tastings and tours",
                "distance_km": 25,
                "specialties": "malvazija_teran_merlot",
                "duration": "2_3_hours",
                "local_tip": "Book the sunset tasting with vineyard tour"
            },
            {
                "name": "Marunada Festival",
                "type": "event",
                "description": "Annual chestnut festival in October with food, music, crafts",
                "distance_km": 0.1,
                "season": "october",
                "highlights": "roasted_chestnuts_local_crafts_folk_music",
                "local_tip": "Come hungry - try maruni in all forms and local honey"
            },
            {
                "name": "Lovranska Draga",
                "type": "village",
                "description": "Charming fishing village with excellent seafood restaurants",
                "distance_km": 2,
                "best_for": "romantic_dinner_sunset",
                "local_tip": "Walk there along the coast path for stunning views"
            }
        ]
    )
    
    try:
        # Get database session
        async for db in get_async_session():
            host_service = HostService(db)
            
            # Check if host already exists
            existing_host = await host_service.get_host_by_email(first_host_data.email)
            if existing_host:
                logger.info(f"Host already exists: {first_host_data.email}")
                return existing_host
            
            # Create the host
            logger.info("Creating first host for Oprić 71, Lovran...")
            created_host = await host_service.create_host(first_host_data)
            
            if not created_host:
                logger.error("Failed to create first host")
                return None
            
            logger.info(f"Host created successfully: {created_host.email}")
            
            # Create the extended profile
            logger.info("Creating extended host profile...")
            profile = await host_service.create_host_profile(created_host.id, profile_data)
            
            if not profile:
                logger.error("Failed to create host profile")
                return created_host
            
            logger.info("Host profile created successfully")
            
            logger.info("=" * 50)
            logger.info("FIRST HOST CREATED SUCCESSFULLY!")
            logger.info("=" * 50)
            logger.info(f"Email: {created_host.email}")
            logger.info(f"Password: {first_host_data.password}")
            logger.info(f"Location: {created_host.address}, {created_host.city}")
            logger.info(f"Business: {created_host.business_name}")
            logger.info(f"Host ID: {created_host.id}")
            logger.info("=" * 50)
            
            return created_host
            
    except Exception as e:
        logger.error(f"Error creating first host: {e}")
        return None


async def main():
    """Main function to run the seed data creation."""
    logging.basicConfig(level=logging.INFO)
    
    logger.info("Starting database seeding for TouristGuideLocal...")
    
    # Create first host
    host = await create_first_host()
    
    if host:
        logger.info("Database seeding completed successfully!")
        logger.info(f"First host created: {host.business_name} in {host.city}")
    else:
        logger.error("Database seeding failed!")


if __name__ == "__main__":
    asyncio.run(main()) 