#!/usr/bin/env python3
"""
Test authentication flow with TEST_USER credentials
"""

import asyncio
import sys
import os
import requests
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

async def test_auth():
    """Test the authentication flow"""
    base_url = "http://localhost:8000"
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Server health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return
    
    # Test 2: Try to login with TEST_USER credentials
    login_data = {
        "email": os.getenv("TEST_USER"),
        "password": os.getenv("TEST_USER_PASS")
    }
    
    print(f"🔐 Attempting login with: {login_data['email']}")
    
    try:
        response = requests.post(f"{base_url}/api/v1/hosts/login", json=login_data)
        print(f"📡 Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"   Session token: {data.get('session_token', 'N/A')[:20]}...")
            print(f"   Refresh token: {data.get('refresh_token', 'N/A')[:20]}...")
            
            # Test 3: Try to get current host with session token
            session_token = data.get('session_token')
            if session_token:
                headers = {"X-Session-Token": session_token}
                me_response = requests.get(f"{base_url}/api/v1/hosts/me", headers=headers)
                print(f"👤 Get current host status: {me_response.status_code}")
                
                if me_response.status_code == 200:
                    host_data = me_response.json()
                    print(f"✅ Host data retrieved successfully!")
                    print(f"   Email: {host_data.get('email', 'N/A')}")
                    print(f"   Name: {host_data.get('first_name', 'N/A')} {host_data.get('last_name', 'N/A')}")
                else:
                    print(f"❌ Failed to get host data: {me_response.text}")
        else:
            print(f"❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"💥 Error during authentication test: {e}")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_auth())
