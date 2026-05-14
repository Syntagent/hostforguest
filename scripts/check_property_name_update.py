import asyncio
from app.core.database import get_db
from sqlalchemy import text

async def check_property_name_update():
    db = await anext(get_db())
    try:
        # Check the test user's profile property_name
        result = await db.execute(
            text("SELECT property_name FROM host_profiles WHERE host_id = (SELECT id FROM hosts WHERE email = 'test@example.com')")
        )
        property_name = result.fetchone()
        print(f"Test user property_name in database: {property_name[0] if property_name else 'None'}")
        
        # Check Benedikt's profile property_name
        result = await db.execute(
            text("SELECT property_name FROM host_profiles WHERE host_id = (SELECT id FROM hosts WHERE email = 'benedikt.perak@gmail.com')")
        )
        property_name = result.fetchone()
        print(f"Benedikt property_name in database: {property_name[0] if property_name else 'None'}")
        
        # Check all profiles to see their property_name values
        result = await db.execute(
            text("SELECT h.email, hp.property_name FROM host_profiles hp JOIN hosts h ON hp.host_id = h.id")
        )
        all_profiles = result.fetchall()
        print(f"\nAll profiles property_name values:")
        for profile in all_profiles:
            print(f"  {profile[0]}: {profile[1]}")
            
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_property_name_update())
