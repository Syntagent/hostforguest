#!/usr/bin/env python3
"""
Simple test for the accommodation update endpoint.
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
        
        # Step 2: Test the update endpoint
        print("\n2️⃣ Testing profile update...")
        headers = {"X-Session-Token": session_token}
        
        update_data = {
            "property_type": "apartment",
            "max_guests": 6,
            "number_of_rooms": 3
        }
        
        update_response = await client.put(
            "http://localhost:8000/api/v1/hosts/me/profile",
            headers=headers,
            json=update_data
        )
        
        print(f"Update response status: {update_response.status_code}")
        print(f"Update response: {update_response.text}")
        
        if update_response.status_code == 200:
            print("✅ Profile update successful!")
        else:
            print("❌ Profile update failed")

if __name__ == "__main__":
    asyncio.run(test_accommodation_update())
