"""
Seed data for Lovran area attractions.

Demonstrates the host knowledge expansion system with initial attractions
that hosts can build upon with their personal insights and local expertise.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import List

from app.models.attraction import (
    AttractionCreate,
    SeasonalEventCreate,
    AttractionType,
    SeasonalAvailability
)

logger = logging.getLogger(__name__)


# Lovran Area Attraction Seed Data
LOVRAN_ATTRACTIONS = [
    {
        "name": "Lungomare Promenade",
        "description": "A beautiful 12-kilometer coastal promenade stretching from Volosko to Lovran, offering stunning views of Kvarner Bay and the islands. This historic walkway, built in the 19th century during Austrian rule, connects charming coastal towns and provides access to hidden beaches and scenic viewpoints.",
        "short_description": "Historic 12km coastal promenade with stunning bay views and hidden beaches",
        "attraction_type": AttractionType.NATURAL,
        "category_tags": ["walking", "scenic", "historic", "family_friendly", "romantic", "photography"],
        "address": "Lungomare, 51415 Lovran, Croatia",
        "city": "Lovran",
        "region": "Kvarner",
        "county": "Primorje-Gorski Kotar",
        "latitude": 45.2919,
        "longitude": 14.2742,
        "host_personal_tip": "Start early morning or late afternoon for the best light and fewer crowds. The section between Opatija and Lovran is the most spectacular.",
        "host_favorite_time": "Golden hour (1 hour before sunset)",
        "host_insider_info": "There's a hidden beach access point near the Villa Angiolina - look for the small stone steps down to the water. Local fishermen often sell fresh catch here in the early morning.",
        "host_story": "I've walked this promenade thousands of times, and it never gets old. My favorite spot is the bench near the old Austrian villa where you can see all the way to Cres island on clear days.",
        "host_recommended_duration": "2-4 hours for full walk",
        "opening_hours": {"everyday": "24/7"},
        "admission_fee": "Free",
        "contact_info": {},
        "difficulty_level": "easy",
        "duration_hours": 3.0,
        "group_size_recommendation": "Perfect for any group size",
        "seasonal_availability": SeasonalAvailability.YEAR_ROUND,
        "best_months": [4, 5, 6, 7, 8, 9, 10],
        "seasonal_notes": "Most beautiful in spring and autumn. Summer can be crowded but offers swimming opportunities.",
        "accessibility_info": {
            "wheelchair_accessible": True,
            "parking": "Available in Opatija and Lovran",
            "public_transport": "Bus stops at both ends"
        },
        "age_suitability": ["children", "adults", "seniors"],
        "required_equipment": ["comfortable_shoes", "sun_protection"],
        "name_translations": {"hr": "Lungomare šetnica", "de": "Lungomare Promenade"},
        "description_translations": {
            "hr": "Prekrasna 12-kilometarska obalna šetnica koja se proteže od Voloska do Lovrana s predivnim pogledom na Kvarnerski zaljev.",
            "de": "Eine wunderschöne 12 Kilometer lange Küstenpromenade von Volosko nach Lovran mit herrlichem Blick auf die Kvarner Bucht."
        },
        "image_gallery": []
    },
    {
        "name": "Učka Nature Park",
        "description": "Croatia's most accessible mountain park, offering hiking trails, panoramic viewpoints, and rich biodiversity. The park covers the entire Učka mountain range with its highest peak Vojak (1,401m) providing 360-degree views of Istria, Kvarner Bay, and the Alps on clear days.",
        "short_description": "Mountain nature park with hiking trails and panoramic views from Vojak peak",
        "attraction_type": AttractionType.NATURAL,
        "category_tags": ["hiking", "nature", "panoramic_views", "adventure", "wildlife", "mountain"],
        "address": "Učka Nature Park, 51414 Ičići, Croatia",
        "city": "Lovran",
        "region": "Kvarner",
        "county": "Primorje-Gorski Kotar",
        "latitude": 45.2936,
        "longitude": 14.2394,
        "host_personal_tip": "Take the Poklon trail to Vojak tower - it's the easiest route to the top. Bring layers as it's always cooler on the mountain.",
        "host_favorite_time": "Early morning for clear views and wildlife spotting",
        "host_insider_info": "The old Učka tunnel entrance makes for great photos, and there's a small mountain hut serving traditional food near Poklon pass.",
        "host_story": "I proposed to my wife at the Vojak tower viewpoint - you can see four countries from there on a clear day!",
        "host_recommended_duration": "Half day to full day",
        "opening_hours": {"everyday": "Always open (tower: 9:00-17:00)"},
        "admission_fee": "Park entry free, Tower 20 HRK",
        "contact_info": {"phone": "+385 51 293 753", "website": "pp-ucka.hr"},
        "difficulty_level": "moderate",
        "duration_hours": 4.0,
        "group_size_recommendation": "Best in small groups (4-8 people)",
        "seasonal_availability": SeasonalAvailability.YEAR_ROUND,
        "best_months": [4, 5, 6, 9, 10],
        "seasonal_notes": "Winter hiking possible but requires experience. Spring offers wildflowers, autumn has spectacular colors.",
        "accessibility_info": {
            "wheelchair_accessible": False,
            "parking": "Available at Poklon pass",
            "mountain_trails": True
        },
        "age_suitability": ["adults", "teenagers"],
        "required_equipment": ["hiking_boots", "weather_protection", "water"],
        "name_translations": {"hr": "Park prirode Učka", "de": "Naturpark Učka"},
        "description_translations": {
            "hr": "Najdostupniji planinski park u Hrvatskoj s planinarskim stazama i panoramskim vidikovcima.",
            "de": "Kroatiens zugänglichster Bergpark mit Wanderwegen und Panoramablicken."
        },
        "image_gallery": []
    },
    {
        "name": "Lovran Old Town",
        "description": "A charming medieval old town with narrow stone streets, historic buildings, and authentic Istrian architecture. The old town features the Church of St. George from the 12th century, traditional stone houses, and several family-run restaurants serving local specialties.",
        "short_description": "Medieval old town with stone streets and 12th century church",
        "attraction_type": AttractionType.HISTORIC,
        "category_tags": ["historic", "architecture", "culture", "walking", "photography", "local_cuisine"],
        "address": "Stari grad Lovran, 51415 Lovran, Croatia",
        "city": "Lovran",
        "region": "Kvarner",
        "county": "Primorje-Gorski Kotar",
        "latitude": 45.2925,
        "longitude": 14.2755,
        "host_personal_tip": "Visit the Church of St. George first, then wander the narrow streets. Try the local restaurant 'Najade' for authentic Istrian cuisine.",
        "host_favorite_time": "Late afternoon when the stone glows golden",
        "host_insider_info": "The old town walls offer the best views - look for the small opening near the church tower. Local cats know all the best sunny spots!",
        "host_story": "My grandmother was born in one of these stone houses. She used to tell stories about the Austrian times and how the whole town would gather in the main square for festivals.",
        "host_recommended_duration": "1-2 hours",
        "opening_hours": {"everyday": "Always accessible"},
        "admission_fee": "Free (church donations welcome)",
        "contact_info": {},
        "difficulty_level": "easy",
        "duration_hours": 1.5,
        "group_size_recommendation": "Perfect for couples or small families",
        "seasonal_availability": SeasonalAvailability.YEAR_ROUND,
        "best_months": [3, 4, 5, 6, 9, 10, 11],
        "seasonal_notes": "Beautiful year-round. Spring and autumn offer comfortable walking weather.",
        "accessibility_info": {
            "wheelchair_accessible": False,
            "historic_stone_streets": True,
            "parking": "Available in new town, 5-minute walk"
        },
        "age_suitability": ["children", "adults", "seniors"],
        "required_equipment": ["comfortable_shoes"],
        "name_translations": {"hr": "Lovranska starina", "de": "Altstadt Lovran"},
        "description_translations": {
            "hr": "Šarmantna srednjovjekovna starina s uskim kamenim uličicama i povijesnim građevinama.",
            "de": "Charmante mittelalterliche Altstadt mit engen Steingassen und historischen Gebäuden."
        },
        "image_gallery": []
    },
    {
        "name": "Medveja Beach",
        "description": "A beautiful pebble beach nestled in a protected bay between Lovran and Opatija. Known for its crystal-clear water, beach bars, and water sports activities. The beach offers both organized sections with amenities and wilder areas for those seeking tranquility.",
        "short_description": "Protected pebble beach with crystal-clear water and beach amenities",
        "attraction_type": AttractionType.NATURAL,
        "category_tags": ["beach", "swimming", "water_sports", "family_friendly", "restaurants"],
        "address": "Medveja Beach, 51415 Lovran, Croatia",
        "city": "Lovran",
        "region": "Kvarner",
        "county": "Primorje-Gorski Kotar",
        "latitude": 45.2889,
        "longitude": 14.2778,
        "host_personal_tip": "Arrive early for the best spots. The left side of the beach is quieter, the right side has more amenities and activities.",
        "host_favorite_time": "Morning for swimming, evening for drinks at the beach bar",
        "host_insider_info": "There's a small hidden cove just 200m north of the main beach - perfect for snorkeling and avoiding crowds.",
        "host_story": "This is where I learned to swim as a child. The water is so clear you can see the bottom even in deeper areas.",
        "host_recommended_duration": "Half day to full day",
        "opening_hours": {"summer": "Lifeguards 9:00-19:00", "winter": "Always accessible"},
        "admission_fee": "Free (sunbed rental available)",
        "contact_info": {"beach_bar": "+385 51 291 234"},
        "difficulty_level": "easy",
        "duration_hours": 4.0,
        "group_size_recommendation": "Great for families and friend groups",
        "seasonal_availability": SeasonalAvailability.SPRING_SUMMER,
        "best_months": [5, 6, 7, 8, 9],
        "seasonal_notes": "Swimming season May-October. Beach bars operate June-September.",
        "accessibility_info": {
            "wheelchair_accessible": "Partially (main entrance only)",
            "parking": "Available above beach",
            "shower_facilities": True
        },
        "age_suitability": ["children", "adults", "families"],
        "required_equipment": ["swimwear", "sun_protection", "water_shoes_recommended"],
        "name_translations": {"hr": "Plaža Medveja", "de": "Strand Medveja"},
        "description_translations": {
            "hr": "Prekrasna šljunčana plaža u zaštićenoj uvali s kristalno čistom vodom.",
            "de": "Wunderschöner Kieselstrand in einer geschützten Bucht mit kristallklarem Wasser."
        },
        "image_gallery": []
    },
    {
        "name": "Villa Angiolina Park",
        "description": "A historic park surrounding the famous Villa Angiolina in Opatija, featuring exotic plants, walking paths, and the Croatian Museum of Tourism. The park was designed in the 19th century and contains over 150 plant species from around the world.",
        "short_description": "Historic 19th-century park with exotic plants and tourism museum",
        "attraction_type": AttractionType.CULTURAL,
        "category_tags": ["historic", "gardens", "museum", "walking", "architecture", "botany"],
        "address": "Park Angiolina, 51410 Opatija, Croatia",
        "city": "Opatija",
        "region": "Kvarner",
        "county": "Primorje-Gorski Kotar",
        "latitude": 45.3378,
        "longitude": 14.3069,
        "host_personal_tip": "Visit the museum first to understand the area's tourism history, then enjoy a peaceful walk through the botanical sections.",
        "host_favorite_time": "Spring when the camellias and magnolias are blooming",
        "host_insider_info": "The Japanese camellia garden is spectacular in March. There's also a small café hidden in the park that serves excellent coffee.",
        "host_story": "This park inspired my love for gardening. I still come here to get ideas for plant combinations in my own garden.",
        "host_recommended_duration": "1-2 hours",
        "opening_hours": {"park": "Always open", "museum": "Tue-Sun 10:00-18:00"},
        "admission_fee": "Park free, Museum 30 HRK",
        "contact_info": {"museum": "+385 51 605 884"},
        "difficulty_level": "easy",
        "duration_hours": 1.5,
        "group_size_recommendation": "Perfect for couples and small groups",
        "seasonal_availability": SeasonalAvailability.YEAR_ROUND,
        "best_months": [3, 4, 5, 6, 9, 10],
        "seasonal_notes": "Spring blooms are spectacular. Autumn colors beautiful. Winter still pleasant for walking.",
        "accessibility_info": {
            "wheelchair_accessible": True,
            "paved_paths": True,
            "parking": "Available nearby"
        },
        "age_suitability": ["children", "adults", "seniors"],
        "required_equipment": [],
        "name_translations": {"hr": "Park Angiolina", "de": "Angiolina Park"},
        "description_translations": {
            "hr": "Povijesni park oko vile Angiolina s egzotičnim biljkama i Hrvatskim muzejom turizma.",
            "de": "Historischer Park um die Villa Angiolina mit exotischen Pflanzen und kroatischem Tourismusmuseum."
        },
        "image_gallery": []
    }
]

# Seasonal Events for Lovran Area
LOVRAN_SEASONAL_EVENTS = [
    {
        "name": "Marunada - Chestnut Festival",
        "description": "The most famous autumn festival in the Kvarner region, celebrating the sweet chestnuts (maruni) that grow on the slopes of Mount Učka. The festival features traditional food, folk music, dancing, and the crowning of the Chestnut Queen. Local restaurants serve special chestnut-based dishes and desserts.",
        "event_type": "festival",
        "location": "Lovran town center",
        "city": "Lovran",
        "venue_details": "Main square and surrounding streets",
        "start_date": date(2024, 10, 12),
        "end_date": date(2024, 10, 20),
        "recurring_pattern": "Annual - October",
        "time_of_day": "All day event",
        "host_recommendation": "Don't miss the traditional chestnut roasting demonstrations and try the maruni cake at local pastry shops.",
        "best_time_to_visit": "Weekend afternoons for the best atmosphere and activities",
        "what_to_expect": "Street food stalls, folk performances, traditional crafts, chestnut-themed dishes, and a festive atmosphere throughout the old town.",
        "host_personal_experience": "I've been coming to Marunada since childhood. The smell of roasted chestnuts and the sound of traditional music create magic in our little town.",
        "admission_info": "Free entry to festival, food and drinks purchased separately",
        "booking_required": False,
        "contact_info": {"website": "tz-lovran.hr", "phone": "+385 51 291 740"}
    },
    {
        "name": "Cherry Days (Dani trešanja)",
        "description": "A spring celebration of the cherry harvest in the Lovran area. The festival includes cherry picking experiences, traditional cherry dishes, folk performances, and the selection of the Cherry Princess. Local producers offer tastings of cherry products including jams, liqueurs, and desserts.",
        "event_type": "festival",
        "location": "Lovran and surrounding villages",
        "city": "Lovran",
        "venue_details": "Various locations including cherry orchards",
        "start_date": date(2024, 6, 1),
        "end_date": date(2024, 6, 9),
        "recurring_pattern": "Annual - Early June",
        "time_of_day": "Morning and afternoon activities",
        "host_recommendation": "Join the cherry picking tours in the morning when it's cooler, and try the cherry strudel at local bakeries.",
        "best_time_to_visit": "Early morning for picking, afternoon for tastings",
        "what_to_expect": "Cherry orchard visits, traditional food preparation demonstrations, folk dancing, and plenty of cherry-themed treats.",
        "host_personal_experience": "My family has a small cherry orchard on the hillside. During Cherry Days, we open it to visitors and share our grandmother's cherry jam recipe.",
        "admission_info": "Free festival, cherry picking tours 50-100 HRK per person",
        "booking_required": True,
        "contact_info": {"tourist_office": "+385 51 291 740"}
    },
    {
        "name": "Asparagus Festival",
        "description": "A culinary celebration of wild asparagus (šparoge) that grows abundantly in the Istrian countryside around Lovran. The festival features asparagus hunting expeditions, cooking workshops, and special menus at local restaurants showcasing this seasonal delicacy.",
        "event_type": "culinary_festival",
        "location": "Lovran restaurants and countryside",
        "city": "Lovran",
        "venue_details": "Various restaurants and outdoor locations",
        "start_date": date(2024, 4, 15),
        "end_date": date(2024, 4, 30),
        "recurring_pattern": "Annual - Mid to late April",
        "time_of_day": "Morning expeditions, evening dinners",
        "host_recommendation": "Book the asparagus hunting tour early in the morning, then enjoy a special asparagus dinner at Restaurant Najade.",
        "best_time_to_visit": "Early morning for foraging, evening for dining",
        "what_to_expect": "Guided foraging walks, cooking demonstrations, special restaurant menus, and tastings of asparagus-based dishes.",
        "host_personal_experience": "I learned to identify wild asparagus from my grandfather. Now I take guests on private foraging tours and teach them to make traditional fritaja.",
        "admission_info": "Foraging tours 80-120 HRK, restaurant menus vary",
        "booking_required": True,
        "contact_info": {"restaurant_bookings": "+385 51 291 203"}
    }
]


async def create_lovran_attractions(attraction_service, host_id: str):
    """
    Create initial Lovran area attractions with host insights.
    
    Args:
        attraction_service: AttractionService instance
        host_id: UUID of the host creating these attractions
    """
    logger.info("Creating Lovran area attractions seed data...")
    
    created_attractions = []
    
    for attraction_data in LOVRAN_ATTRACTIONS:
        try:
            # Create AttractionCreate object
            attraction_create = AttractionCreate(**attraction_data)
            
            # Create the attraction
            created_attraction = await attraction_service.create_attraction(
                host_id=host_id,
                attraction_data=attraction_create
            )
            
            if created_attraction:
                # Automatically approve seed data
                await attraction_service.db.execute(
                    update(Attraction).where(Attraction.id == created_attraction.id).values(
                        status=AttractionStatus.APPROVED,
                        approved_at=datetime.utcnow(),
                        approved_by="system_seed",
                        published_at=datetime.utcnow()
                    )
                )
                await attraction_service.db.commit()
                
                created_attractions.append(created_attraction)
                logger.info(f"Created and approved attraction: {attraction_data['name']}")
            else:
                logger.error(f"Failed to create attraction: {attraction_data['name']}")
                
        except Exception as e:
            logger.error(f"Error creating attraction {attraction_data['name']}: {e}")
    
    logger.info(f"Successfully created {len(created_attractions)} Lovran attractions")
    return created_attractions


async def create_lovran_seasonal_events(attraction_service, host_id: str):
    """
    Create seasonal events for Lovran area.
    
    Args:
        attraction_service: AttractionService instance
        host_id: UUID of the host creating these events
    """
    logger.info("Creating Lovran seasonal events seed data...")
    
    created_events = []
    
    for event_data in LOVRAN_SEASONAL_EVENTS:
        try:
            # Create SeasonalEventCreate object
            event_create = SeasonalEventCreate(**event_data)
            
            # Create the event
            created_event = await attraction_service.create_seasonal_event(
                host_id=host_id,
                event_data=event_create
            )
            
            if created_event:
                created_events.append(created_event)
                logger.info(f"Created seasonal event: {event_data['name']}")
            else:
                logger.error(f"Failed to create event: {event_data['name']}")
                
        except Exception as e:
            logger.error(f"Error creating event {event_data['name']}: {e}")
    
    logger.info(f"Successfully created {len(created_events)} Lovran seasonal events")
    return created_events


# Host expansion examples - showing how hosts can add their personal touch
HOST_EXPANSION_EXAMPLES = {
    "personal_tips": [
        "The best gelato in Opatija is at Slastičarna Rigo - try the fig flavor!",
        "For sunrise photos at Učka, start hiking at 5 AM in summer",
        "Local fishermen sell fresh catch at the small harbor every morning around 7 AM",
        "The hidden waterfall near Lovranska Draga is perfect for hot summer days"
    ],
    "insider_secrets": [
        "There's a secret beach accessible only at low tide near Medveja",
        "The old Austrian bunkers on Učka make for great exploration",
        "Local restaurant Plavi Podrum has the best truffle pasta but it's not on the menu - just ask",
        "The cemetery above Lovran has the most beautiful sunset views"
    ],
    "seasonal_insights": [
        "Wild asparagus season is short - usually just 3-4 weeks in April",
        "Chestnut season varies yearly but usually peaks mid-October",
        "Swimming season can start as early as May if you're brave!",
        "Winter storms create spectacular wave watching at Lungomare"
    ],
    "host_stories": [
        "My great-grandfather built part of the Lungomare with his own hands",
        "I proposed to my wife at the Vojak tower viewpoint",
        "Our family has been making cherry jam for four generations",
        "I've seen dolphins from my balcony three times this year"
    ]
}

if __name__ == "__main__":
    print("Lovran attractions seed data ready for import")
    print(f"Total attractions: {len(LOVRAN_ATTRACTIONS)}")
    print(f"Total seasonal events: {len(LOVRAN_SEASONAL_EVENTS)}")
    print("This data demonstrates the host knowledge expansion system") 