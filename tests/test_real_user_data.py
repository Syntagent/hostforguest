#!/usr/bin/env python3
"""
Test script to verify real user data access with PostgreSQL.
Tests the system with real user credentials to ensure data is coming from the database.
"""

import requests
import json
import sys

def test_real_user_data():
    """Test real user data access with benedikt.perak@gmail.com"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Real User Data Access")
    print("=" * 50)
    
    # Step 1: Login with real credentials
    print("\n1. Testing login...")
    login_data = {
        "email": "benedikt.perak@gmail.com",
        "password": "sunriseheights"
    }
    
    try:
        login_response = requests.post(f"{base_url}/api/v1/hosts/login", json=login_data)
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            return False
            
        login_result = login_response.json()
        session_token = login_result["session_token"]
        host_data = login_result["host"]
        
        print(f"✅ Login successful!")
        print(f"Host ID: {host_data['id']}")
        print(f"Host Name: {host_data['first_name']} {host_data['last_name']}")
        print(f"Email: {host_data['email']}")
        print(f"Business Type: {host_data['business_type']}")
        print(f"Address: {host_data['address']}")
        print(f"Total Guest Groups: {host_data['total_guest_groups']}")
        print(f"Average Rating: {host_data['average_rating']}")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Step 2: Test profile endpoint
    print("\n2. Testing profile endpoint...")
    try:
        profile_response = requests.get(
            f"{base_url}/api/v1/hosts/me/profile",
            headers={"X-Session-Token": session_token}
        )
        print(f"Profile status: {profile_response.status_code}")
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print("✅ Profile data retrieved successfully!")
            print(f"Profile ID: {profile_data.get('id', 'N/A')}")
            print(f"Business Name: {profile_data.get('business_name', 'N/A')}")
        elif profile_response.status_code == 404:
            print("ℹ️ No profile found (this is expected for new users)")
        else:
            print(f"❌ Profile error: {profile_response.text}")
            
    except Exception as e:
        print(f"❌ Profile error: {e}")
    
    # Step 3: Test analytics endpoint
    print("\n3. Testing analytics endpoint...")
    try:
        analytics_response = requests.get(
            f"{base_url}/api/v1/hosts/analytics",
            headers={"X-Session-Token": session_token}
        )
        print(f"Analytics status: {analytics_response.status_code}")
        
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
            print("✅ Analytics data retrieved successfully!")
            print("Analytics breakdown:")
            print(f"  - Guest Groups: {analytics_data.get('guest_groups', {})}")
            print(f"  - Attractions: {analytics_data.get('attractions', {})}")
            print(f"  - Recommendations: {analytics_data.get('recommendations', {})}")
            print(f"  - Satisfaction: {analytics_data.get('satisfaction', {})}")
        else:
            print(f"❌ Analytics error: {analytics_response.text}")
            
    except Exception as e:
        print(f"❌ Analytics error: {e}")
    
    # Step 4: Test guest groups endpoint
    print("\n4. Testing guest groups endpoint...")
    try:
        groups_response = requests.get(
            f"{base_url}/api/v1/guest-groups/host",
            headers={"X-Session-Token": session_token}
        )
        print(f"Guest Groups status: {groups_response.status_code}")
        
        if groups_response.status_code == 200:
            groups_data = groups_response.json()
            print(f"✅ Guest groups retrieved: {len(groups_data)} groups")
            for group in groups_data:
                print(f"  - {group.get('group_name', 'N/A')} ({group.get('status', 'N/A')})")
        else:
            print(f"❌ Guest groups error: {groups_response.text}")
            
    except Exception as e:
        print(f"❌ Guest groups error: {e}")
    
    # Step 5: Test attractions endpoint
    print("\n5. Testing attractions endpoint...")
    try:
        attractions_response = requests.get(
            f"{base_url}/api/v1/attractions/host",
            headers={"X-Session-Token": session_token}
        )
        print(f"Attractions status: {attractions_response.status_code}")
        
        if attractions_response.status_code == 200:
            attractions_data = attractions_response.json()
            print(f"✅ Attractions retrieved: {len(attractions_data)} attractions")
            for attraction in attractions_data:
                print(f"  - {attraction.get('name', 'N/A')} ({attraction.get('category', 'N/A')})")
        else:
            print(f"❌ Attractions error: {attractions_response.text}")
            
    except Exception as e:
        print(f"❌ Attractions error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Real User Data Test Complete")
    
    return True

if __name__ == "__main__":
    success = test_real_user_data()
    sys.exit(0 if success else 1)
