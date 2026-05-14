"""
Complete Onboarding Flow Test Script

Tests all backend API endpoints involved in the host onboarding process:
1. Host registration
2. Login
3. Basic info submission
4. AI profile generation
5. Attraction suggestions
6. Final onboarding completion
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Test data
TEST_HOST = {
    "email": f"test.host.{datetime.now().timestamp()}@example.com",
    "password": "TestPassword123!",
    "first_name": "Marina",
    "last_name": "Kovač",
    "address": "Maršala Tita 123, 51410 Opatija",
    "city": "Opatija"
}

# Session tokens
session_token = None
refresh_token = None
host_id = None

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_result(success, message, data=None):
    """Print test result"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"\n{status}: {message}")
    if data:
        print(f"Response: {json.dumps(data, indent=2)}")

def test_1_register_host():
    """Test host registration"""
    global host_id
    print_section("TEST 1: Host Registration")
    
    try:
        response = requests.post(
            f"{API_URL}/hosts/register",
            json=TEST_HOST
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 201 and data.get("id"):
            host_id = data["id"]
            print_result(True, "Host registered successfully", {
                "host_id": host_id,
                "email": data.get("email"),
                "first_name": data.get("first_name")
            })
            return True
        else:
            print_result(False, "Registration failed", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during registration: {str(e)}")
        return False

def test_2_login():
    """Test host login"""
    global session_token, refresh_token
    print_section("TEST 2: Host Login")
    
    try:
        response = requests.post(
            f"{API_URL}/hosts/login",
            json={
                "email": TEST_HOST["email"],
                "password": TEST_HOST["password"]
            }
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("session_token"):
            session_token = data["session_token"]
            refresh_token = data.get("refresh_token")
            print_result(True, "Login successful", {
                "session_token": session_token[:20] + "...",
                "refresh_token": refresh_token[:20] + "..." if refresh_token else None,
                "host_id": data.get("host_id")
            })
            return True
        else:
            print_result(False, "Login failed", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during login: {str(e)}")
        return False

def test_3_get_profile():
    """Test getting current host profile"""
    print_section("TEST 3: Get Host Profile")
    
    try:
        response = requests.get(
            f"{API_URL}/hosts/me",
            headers={"Authorization": f"Bearer {session_token}"}
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200:
            print_result(True, "Profile retrieved successfully", {
                "email": data.get("email"),
                "first_name": data.get("first_name"),
                "onboarding_completed": data.get("onboarding_completed")
            })
            return True
        else:
            print_result(False, "Failed to get profile", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception getting profile: {str(e)}")
        return False

def test_4_ai_profile_suggestions():
    """Test AI profile generation"""
    print_section("TEST 4: AI Profile Suggestions")
    
    try:
        response = requests.post(
            f"{API_URL}/onboarding/ai-profile",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "first_name": TEST_HOST["first_name"],
                "last_name": TEST_HOST["last_name"],
                "city": TEST_HOST["city"],
                "property_type": "villa",
                "local_experience": "born_here",
                "interests": ["Local History", "Gastronomy"],
                "target_guests": ["families", "couples"]
            }
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            print_result(True, "AI profile generated", {
                "suggestions_count": len(data.get("ai_suggestions", {}).get("business_description", [])),
                "has_welcome_message": bool(data.get("ai_suggestions", {}).get("welcome_message"))
            })
            return True
        else:
            print_result(False, "AI profile generation failed", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during AI profile generation: {str(e)}")
        return False

def test_5_attraction_suggestions():
    """Test attraction suggestions"""
    print_section("TEST 5: Attraction Suggestions")
    
    try:
        response = requests.post(
            f"{API_URL}/onboarding/attractions/suggestions",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "city": "Opatija",
                "region": "Kvarner",
                "interests": ["Local History", "Gastronomy", "Nature Activities"],
                "preferred_guests": ["Young couples", "Families with children"],
                "local_experience": "born_here",
                "knowledge_level": "expert",
                "location_story": "My family has owned this beautiful villa in Opatija for three generations."
            }
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            attractions = data.get("attractions", [])
            print_result(True, "Attractions generated", {
                "total_attractions": data.get("total_count", 0),
                "first_attraction": attractions[0].get("name") if attractions else None
            })
            return True
        else:
            print_result(False, "Attraction generation failed", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during attraction generation: {str(e)}")
        return False

def test_6_complete_onboarding():
    """Test onboarding completion"""
    print_section("TEST 6: Complete Onboarding")
    
    try:
        response = requests.post(
            f"{API_URL}/onboarding/complete-onboarding",
            headers={"Authorization": f"Bearer {session_token}"},
            json={
                "city": "Opatija",
                "region": "Kvarner",
                "address": "Maršala Tita 123, 51410 Opatija, Croatia",
                "interests": ["Local History", "Gastronomy", "Nature Activities"],
                "preferred_guests": ["Young couples", "Families with children"],
                "local_experience": "born_here",
                "knowledge_level": "expert",
                "location_story": "My family has owned this beautiful villa in Opatija for three generations. We know every hidden beach, the best hiking trails in Učka Nature Park, and where to find authentic Kvarner cuisine."
            }
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            print_result(True, "Onboarding completed!", {
                "host_id": data.get("host_id"),
                "guest_access_code": data.get("guest_access_code"),
                "profile_updated": data.get("profile_updated")
            })
            return True
        else:
            print_result(False, "Onboarding completion failed", data)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during onboarding completion: {str(e)}")
        return False

def test_7_guest_access():
    """Test guest access with the generated code"""
    print_section("TEST 7: Guest Access (Bonus)")
    
    try:
        # First, get the access code by checking the host profile
        profile_response = requests.get(
            f"{API_URL}/hosts/me",
            headers={"Authorization": f"Bearer {session_token}"}
        )
        
        if profile_response.status_code == 200:
            access_code = profile_response.json().get("guest_access_code")
            
            if access_code:
                # Test guest access endpoint
                response = requests.get(
                    f"{API_URL}/onboarding/guest-access/{access_code}"
                )
                
                print(f"Status Code: {response.status_code}")
                data = response.json()
                
                if response.status_code == 200 and data.get("success"):
                    print_result(True, "Guest access works!", {
                        "host_name": data.get("host_offerings", {}).get("host_info", {}).get("name"),
                        "city": data.get("host_offerings", {}).get("location_info", {}).get("city"),
                        "access_code": access_code
                    })
                    return True
                else:
                    print_result(False, "Guest access failed", data)
                    return False
            else:
                print_result(False, "No access code generated", None)
                return False
        else:
            print_result(False, "Could not retrieve host profile", None)
            return False
            
    except Exception as e:
        print_result(False, f"Exception during guest access test: {str(e)}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "🚀 "*20)
    print("COMPLETE ONBOARDING FLOW TEST")
    print("🚀 "*20)
    
    results = []
    
    # Run tests in order
    results.append(("Registration", test_1_register_host()))
    if not results[-1][1]:
        print("\n❌ Cannot proceed without successful registration")
        return
    
    results.append(("Login", test_2_login()))
    if not results[-1][1]:
        print("\n❌ Cannot proceed without successful login")
        return
    
    results.append(("Get Profile", test_3_get_profile()))
    results.append(("AI Profile", test_4_ai_profile_suggestions()))
    results.append(("Attractions", test_5_attraction_suggestions()))
    results.append(("Complete Onboarding", test_6_complete_onboarding()))
    results.append(("Guest Access", test_7_guest_access()))
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The onboarding flow is working correctly!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")

if __name__ == "__main__":
    run_all_tests()
