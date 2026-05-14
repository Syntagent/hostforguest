import asyncio
from app.core.database import get_db
from app.services.host_service import HostService
from app.models.host import HostProfileUpdate
from sqlalchemy import text

async def test_backend_service():
    db = await anext(get_db())
    try:
        # Get the test user's host ID
        result = await db.execute(
            text("SELECT id FROM hosts WHERE email = 'test@example.com'")
        )
        host_id = result.fetchone()[0]
        print(f"Test user host ID: {host_id}")
        
        # Create the service
        host_service = HostService(db)
        
        # Test the update method directly
        print("Testing HostService.update_host_profile directly...")
        
        update_data = HostProfileUpdate(
            property_name="Villa Adriatica žđ",
            property_type="apartment",
            max_guests=6,
            number_of_rooms=3
        )
        
        print(f"Update data: {update_data}")
        
        try:
            result = await host_service.update_host_profile(host_id, update_data)
            if result:
                print(f"✅ Service update successful!")
                print(f"Result: {result}")
            else:
                print(f"❌ Service update returned None")
        except Exception as e:
            print(f"❌ Service update failed with exception: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_backend_service())
