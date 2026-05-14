#!/usr/bin/env python3
"""
Test script to verify the accommodation API endpoint with corrected data structure.
"""

import httpx
import asyncio
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def test_accommodation_api():
    """Test the accommodation API endpoint with corrected data structure."""
    
    # Get test credentials from .env
    test_user = os.getenv('TEST_USER')
    test_pass = os.getenv('TEST_USER_PASS')
    
    if not test_user or not test_pass:
        print("❌ TEST_USER or TEST_USER_PASS not found in .env file")
        return
    
    base_url = "http://localhost:8000"
    
    # First, login to get session token
    print("🔐 Logging in to get session token...")
    
    login_data = {
        "email": test_user,
        "password": test_pass
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Login
            login_response = await client.post(
                f"{base_url}/api/v1/auth/login",
                json=login_data
            )
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"Response: {login_response.text}")
                return
            
            login_result = login_response.json()
            session_token = login_result.get('session_token')
            
            if not session_token:
                print("❌ No session token received")
                return
            
            print(f"✅ Login successful, session token: {session_token[:20]}...")
            
            # Test the accommodation update endpoint with corrected data structure
            print("\n🔄 Testing accommodation update endpoint...")
            
            # This is the corrected data structure that should work
            update_data = {
                "property_name": "apartment",
                "property_type": "apartment",
                "max_guests": 12,
                "number_of_rooms": 3,
                "amenities": [],  # Empty list, not nested object
                "services_offered": [],  # Empty list, not nested object
                "expertise_areas": [],  # Empty list, not nested object
                "location_story": "No description available",
                "city": "Lovran",
                "county": "Hrvatska",
                "address": "71, 51415, Oprić, Croatia",
                "latitude": 45.3110082,
                "longitude": 14.2705425
            }
            
            print(f"📋 Sending data: {json.dumps(update_data, indent=2)}")
            
            # Make the update request
            update_response = await client.put(
                f"{base_url}/api/v1/hosts/me/profile",
                json=update_data,
                headers={"X-Session-Token": session_token}
            )
            
            print(f"📡 Response status: {update_response.status_code}")
            print(f"📡 Response headers: {dict(update_response.headers)}")
            
            if update_response.status_code == 200:
                print("✅ Accommodation update successful!")
                result = update_response.json()
                print(f"📋 Response data: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ Accommodation update failed: {update_response.status_code}")
                print(f"📋 Response: {update_response.text}")
                
                # Try to parse error details
                try:
                    error_data = update_response.json()
                    if 'detail' in error_data:
                        print(f"🔍 Error details: {json.dumps(error_data['detail'], indent=2)}")
                except:
                    pass
                    
        except Exception as e:
            print(f"💥 Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_accommodation_api())
