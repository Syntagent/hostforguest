#!/usr/bin/env python3
"""
Test script for the new accommodation update endpoint.
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

async def test_accommodation_update():
    """Test the accommodation update endpoint."""
    
    # Get test credentials from .env
    test_user = os.getenv('TEST_USER')
    test_pass = os.getenv('TEST_USER_PASS')
    
    if not test_user or not test_pass:
        print("❌ TEST_USER and TEST_USER_PASS not found in .env file")
        return
    
    print(f"🧪 Testing accommodation update for user: {test_user}")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Login to get session token
        print("\n1️⃣ Logging in...")
        login_response = await client.post(
            "http://localhost:8000/api/v1/hosts/login",
            json={
                "email": test_user,
                "password": test_pass
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            return
        
        login_data = login_response.json()
        session_token = login_data.get("session_token")
        
        if not session_token:
            print("❌ No session token received")
            return
        
        print("✅ Login successful")
        print(f"📝 Session token: {session_token[:20]}...")
        
        # Step 2: Get current profile
        print("\n2️⃣ Getting current profile...")
        headers = {"X-Session-Token": session_token}
        
        profile_response = await client.get(
            "http://localhost:8000/api/v1/hosts/me/profile",
            headers=headers
        )
        
        if profile_response.status_code != 200:
            print(f"❌ Failed to get profile: {profile_response.status_code}")
            print(profile_response.text)
            return
        
        current_profile = profile_response.json()
        print("✅ Current profile retrieved")
        print(f"📋 Property type: {current_profile.get('property_type', 'Not set')}")
        print(f"🏠 Max guests: {current_profile.get('max_guests', 'Not set')}")
        
        # Step 3: Update profile with new data
        print("\n3️⃣ Updating profile...")
        
        update_data = {
            "property_type": "apartment",
            "max_guests": 6,
            "number_of_rooms": 3,
            "amenities": ["wifi", "parking", "kitchen", "balcony"],
            "services_offered": ["airport_transfer", "guided_tours"],
            "expertise_areas": ["Local History", "Wine Tourism"],
            "location_story": "Our charming apartment is located in the heart of Rijeka, offering easy access to all major attractions and beautiful coastal views."
        }
        
        update_response = await client.put(
            "http://localhost:8000/api/v1/hosts/me/profile",
            headers=headers,
            json=update_data
        )
        
        if update_response.status_code != 200:
            print(f"❌ Profile update failed: {update_response.status_code}")
            print(update_response.text)
            return
        
        updated_profile = update_response.json()
        print("✅ Profile updated successfully")
        print(f"📋 New property type: {updated_profile.get('property_type')}")
        print(f"🏠 New max guests: {updated_profile.get('max_guests')}")
        print(f"📍 Location story: {updated_profile.get('location_story', 'Not set')[:50]}...")
        
        # Step 4: Verify the update by getting profile again
        print("\n4️⃣ Verifying update...")
        verify_response = await client.get(
            "http://localhost:8000/api/v1/hosts/me/profile",
            headers=headers
        )
        
        if verify_response.status_code != 200:
            print(f"❌ Failed to verify profile: {verify_response.status_code}")
            return
        
        verified_profile = verify_response.json()
        print("✅ Profile verification successful")
        print(f"📋 Verified property type: {verified_profile.get('property_type')}")
        print(f"🏠 Verified max guests: {verified_profile.get('max_guests')}")
        
        print("\n🎉 All tests passed! Accommodation update endpoint is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_accommodation_update())
