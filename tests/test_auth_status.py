#!/usr/bin/env python3
"""
Test script to check authentication status and session tokens
"""
import os
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_auth_status():
    """Test the authentication endpoints to see what's happening"""
    
    # Get test credentials from .env
    test_user = os.getenv('TEST_USER')
    test_pass = os.getenv('TEST_USER_PASS')
    
    if not test_user or not test_pass:
        print("❌ TEST_USER or TEST_USER_PASS not found in .env")
        return
    
    print(f"🔐 Testing authentication for user: {test_user}")
    
    async with httpx.AsyncClient() as client:
        # 1. Try to login first
        print("\n1️⃣ Attempting login...")
        login_data = {
            "email": test_user,
            "password": test_pass
        }
        
        try:
            login_response = await client.post(
                "http://localhost:8000/api/v1/hosts/login",
                json=login_data
            )
            
            print(f"📡 Login Response Status: {login_response.status_code}")
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                print("✅ Login successful!")
                print(f"📋 Session Token: {login_data.get('session_token', 'Not found')[:20]}...")
                print(f"📋 Refresh Token: {login_data.get('refresh_token', 'Not found')[:20]}...")
                
                # Extract session token
                session_token = login_data.get('session_token')
                
                if session_token:
                    # 2. Try to get current host with session token
                    print("\n2️⃣ Testing GET /api/v1/hosts/me with session token...")
                    
                    headers = {
                        "X-Session-Token": session_token,
                        "Content-Type": "application/json"
                    }
                    
                    me_response = await client.get(
                        "http://localhost:8000/api/v1/hosts/me",
                        headers=headers
                    )
                    
                    print(f"📡 GET /hosts/me Response Status: {me_response.status_code}")
                    
                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        print("✅ GET /hosts/me successful!")
                        print(f"📋 Host Data: {me_data}")
                    else:
                        print(f"❌ GET /hosts/me failed: {me_response.text}")
                        
                        # Try to get more details about the error
                        try:
                            error_data = me_response.json()
                            print(f"📋 Error Details: {error_data}")
                        except:
                            print(f"📋 Raw Error: {me_response.text}")
                    
                    # 3. Try to get host profile
                    print("\n3️⃣ Testing GET /api/v1/hosts/me/profile with session token...")
                    
                    profile_response = await client.get(
                        "http://localhost:8000/api/v1/hosts/me/profile",
                        headers=headers
                    )
                    
                    print(f"📡 GET /hosts/me/profile Response Status: {profile_response.status_code}")
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        print("✅ GET /hosts/me/profile successful!")
                        print(f"📋 Profile Data: {profile_data}")
                    else:
                        print(f"❌ GET /hosts/me/profile failed: {profile_response.text}")
                        
                        try:
                            error_data = profile_response.json()
                            print(f"📋 Error Details: {error_data}")
                        except:
                            print(f"📋 Raw Error: {profile_response.text}")
                
            else:
                print(f"❌ Login failed: {login_response.text}")
                
        except Exception as e:
            print(f"💥 Error during login: {e}")
        
        # 4. Test without session token (should fail)
        print("\n4️⃣ Testing GET /api/v1/hosts/me without session token...")
        
        try:
            no_token_response = await client.get("http://localhost:8000/api/v1/hosts/me")
            print(f"📡 No Token Response Status: {no_token_response.status_code}")
            
            if no_token_response.status_code == 401:
                print("✅ Correctly rejected without session token")
            else:
                print(f"⚠️ Unexpected response without token: {no_token_response.text}")
                
        except Exception as e:
            print(f"💥 Error testing without token: {e}")

if __name__ == "__main__":
    print("🚀 Starting Authentication Status Test")
    print("=" * 50)
    
    asyncio.run(test_auth_status())
    
    print("\n" + "=" * 50)
    print("🏁 Authentication Status Test Complete")

