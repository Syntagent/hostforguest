#!/usr/bin/env python3
"""
Debug the onboarding endpoint specifically
"""

import asyncio
import httpx
import json

async def debug_onboarding():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First login
        login_data = {
            "email": "real.test@lovran.hr",
            "password": "testpass123"
        }
        
        login_response = await client.post(
            "http://localhost:8000/api/v1/hosts/login",
            json=login_data
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return
        
        result = login_response.json()
        token = result["access_token"]
        print(f"✅ Login successful, token: {token[:20]}...")
        
        # Try onboarding with minimal data first
        minimal_data = {
            "city": "Lovran",
            "interests": ["food"],
            "preferred_guests": ["families"],
            "knowledge_level": "expert"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        print("🧪 Testing minimal onboarding data...")
        onboard_response = await client.post(
            "http://localhost:8000/api/v1/onboarding/complete-onboarding",
            json=minimal_data,
            headers=headers
        )
        
        print(f"Status: {onboard_response.status_code}")
        print(f"Response: {onboard_response.text}")

if __name__ == "__main__":
    asyncio.run(debug_onboarding())
