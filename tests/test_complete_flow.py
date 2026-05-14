#!/usr/bin/env python3
"""
REAL TESTING - Complete Host-Guest Flow Validation
Tests the entire system end-to-end to prove it actually works.
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_HOST_EMAIL = "real.test@lovran.hr"
TEST_HOST_PASSWORD = "testpass123"

class TouristGuideSystemTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.host_token = None
        self.host_id = None
        self.access_code = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "TEST": "🧪"}
        print(f"{status_emoji.get(status, 'ℹ️')} [{timestamp}] {message}")
    
    async def test_1_host_registration(self):
        """Test host registration - Step 1 of the flow"""
        self.log("Testing host registration...", "TEST")
        
        host_data = {
            "email": TEST_HOST_EMAIL,
            "password": TEST_HOST_PASSWORD,
            "first_name": "Marija",
            "last_name": "Testović",
            "phone": "+385 51 123 456",
            "business_name": "Villa Marija Test",
            "business_type": "villa",
            "address": "Šetalište Marsala Tita 15, Lovran",
            "city": "Lovran",
            "county": "Istria",
            "postal_code": "51415",
            "country": "Croatia",
            "max_group_size": 8,
            "description": "Beautiful test villa with sea view",
            "welcome_message": "Welcome to our test villa in Lovran!"
        }
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/hosts/register",
                json=host_data
            )
            
            if response.status_code == 201:
                result = response.json()
                self.host_id = result["id"]
                self.log(f"Host registered successfully! ID: {self.host_id}", "SUCCESS")
                return True
            elif response.status_code == 400:
                self.log("Host already exists, continuing...", "INFO")
                return True
            else:
                self.log(f"Registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Registration error: {e}", "ERROR")
            return False
    
    async def test_2_host_login(self):
        """Test host authentication - Step 2"""
        self.log("Testing host login...", "TEST")
        
        login_data = {
            "email": TEST_HOST_EMAIL,
            "password": TEST_HOST_PASSWORD
        }
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/hosts/login",
                json=login_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.host_token = result["access_token"]
                self.host_id = result["host_id"]
                self.log("Host login successful!", "SUCCESS")
                return True
            else:
                self.log(f"Login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Login error: {e}", "ERROR")
            return False
    
    async def test_3_complete_onboarding(self):
        """Test completing onboarding and saving to database - Step 3"""
        self.log("Testing onboarding completion...", "TEST")
        
        onboarding_data = {
            "city": "Lovran",
            "region": "Istria",
            "address": "Šetalište Marsala Tita 15, Lovran",
            "coordinates": {
                "lat": 45.2969275,
                "lng": 14.2723701
            },
            "interests": ["food", "nature", "culture", "beaches", "wine"],
            "local_experience": "born_here",
            "preferred_guests": ["families", "couples", "food_lovers"],
            "location_story": "My family has lived in Lovran for three generations. We know every secret beach, hidden restaurant, and local tradition. Our villa has hosted guests from all over the world, and we love sharing the authentic Istrian experience.",
            "knowledge_level": "expert"
        }
        
        headers = {"Authorization": f"Bearer {self.host_token}"}
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/onboarding/complete-onboarding",
                json=onboarding_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.access_code = result["guest_access_code"]
                    self.log(f"Onboarding completed! Access code: {self.access_code}", "SUCCESS")
                    self.log(f"Attractions generated: {result.get('attractions_generated', 0)}", "INFO")
                    return True
                else:
                    self.log(f"Onboarding failed: {result}", "ERROR")
                    return False
            else:
                self.log(f"Onboarding failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Onboarding error: {e}", "ERROR")
            return False
    
    async def test_4_guest_access(self):
        """Test guest accessing host offerings - Step 4"""
        self.log(f"Testing guest access with code: {self.access_code}", "TEST")
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/onboarding/guest-access/{self.access_code}"
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    host_info = result["host_offerings"]["host_info"]
                    recommendations = result["host_offerings"]["recommendations"]
                    
                    self.log(f"Guest access successful! Host: {host_info['name']}", "SUCCESS")
                    self.log(f"Location: {host_info['city']}", "INFO")
                    self.log(f"Attractions available: {len(recommendations.get('attractions', []))}", "INFO")
                    self.log(f"Expertise areas: {len(recommendations.get('expertise_areas', []))}", "INFO")
                    return True
                else:
                    self.log(f"Guest access failed: {result}", "ERROR")
                    return False
            else:
                self.log(f"Guest access failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Guest access error: {e}", "ERROR")
            return False
    
    async def test_5_guest_messaging(self):
        """Test guest-host communication - Step 5"""
        self.log("Testing guest messaging system...", "TEST")
        
        message_data = {
            "message": "Hi! Can you recommend some local restaurants for dinner tonight?",
            "type": "question",
            "guest_name": "John Traveler"
        }
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/onboarding/guest-message/{self.access_code}",
                json=message_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log("Guest messaging successful!", "SUCCESS")
                    self.log(f"Response type: {result.get('response_type')}", "INFO")
                    self.log(f"AI response: {result.get('message', '')[:100]}...", "INFO")
                    self.log(f"Suggestions provided: {len(result.get('suggestions', []))}", "INFO")
                    return True
                else:
                    self.log(f"Messaging failed: {result}", "ERROR")
                    return False
            else:
                self.log(f"Messaging failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Messaging error: {e}", "ERROR")
            return False
    
    async def run_complete_test(self):
        """Run the complete end-to-end test"""
        self.log("🚀 Starting COMPLETE SYSTEM TEST", "INFO")
        self.log("=" * 50, "INFO")
        
        tests = [
            ("Host Registration", self.test_1_host_registration),
            ("Host Authentication", self.test_2_host_login),
            ("Onboarding Completion", self.test_3_complete_onboarding),
            ("Guest Access", self.test_4_guest_access),
            ("Guest Messaging", self.test_5_guest_messaging)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---", "INFO")
            try:
                result = await test_func()
                results[test_name] = result
                if not result:
                    self.log(f"❌ {test_name} FAILED - stopping tests", "ERROR")
                    break
            except Exception as e:
                self.log(f"❌ {test_name} CRASHED: {e}", "ERROR")
                results[test_name] = False
                break
        
        # Final results
        self.log("\n" + "=" * 50, "INFO")
        self.log("🏁 FINAL TEST RESULTS", "INFO")
        self.log("=" * 50, "INFO")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} {test_name}", "SUCCESS" if result else "ERROR")
        
        self.log(f"\nOVERALL: {passed}/{total} tests passed", "SUCCESS" if passed == total else "ERROR")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED! The system works end-to-end!", "SUCCESS")
            self.log(f"🔑 Guest Access Code: {self.access_code}", "INFO")
            self.log(f"🌐 Guest URL: http://localhost:3000/guest/{self.access_code}", "INFO")
        else:
            self.log("💥 SYSTEM HAS ISSUES - Some tests failed!", "ERROR")
        
        return passed == total

async def main():
    tester = TouristGuideSystemTester()
    try:
        success = await tester.run_complete_test()
        sys.exit(0 if success else 1)
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
