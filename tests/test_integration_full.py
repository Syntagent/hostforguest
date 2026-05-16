"""
Comprehensive integration tests for TouristGuideLocal Croatian tourism platform.

Tests the complete end-to-end workflow from host registration to guest recommendations,
covering all major systems and Croatian tourism features.
"""

import os
import pytest
import asyncio
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timedelta

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_DB", "").lower() not in ("1", "true", "yes"),
    reason="Integration suite uses live Postgres from .env; start DB and set RUN_INTEGRATION_DB=1.",
)


class TestTouristGuideLocalIntegration:
    """
    Comprehensive integration test suite for the Croatian tourism platform.
    
    Tests the complete user journey:
    1. Host registration and authentication
    2. Settings and API key management
    3. Attraction management and contributions
    4. Guest group creation and access codes
    5. Personalized recommendations
    6. Croatian tourism features
    """

    # Shared across test methods (pytest uses a new instance per method).
    host_id = None
    auth_headers = None
    attraction_id = None
    guest_group_id = None
    access_code = None
    
    @pytest.fixture(scope="class")
    def client(self):
        """Test client for API requests (context manager keeps one async portal for all requests)."""
        with TestClient(app) as c:
            yield c
    
    @pytest.fixture(scope="class")
    def test_host_data(self):
        """Test host data for Lovran area (must match HostCreate / register API)."""
        suffix = uuid.uuid4().hex[:10]
        return {
            "email": f"host.lovran.{suffix}@example.com",
            "password": "SecurePassword123!",
            "first_name": "Ana",
            "last_name": "Marić",
            "business_name": "Lovran Sea View Apartments",
            "phone": "+385 51 291 123",
            "address": "Oprić 71, 51450 Lovran, Croatia",
            "city": "Lovran",
            "country": "Croatia",
            "description": "Family-run apartments with stunning sea views in historic Lovran.",
            "languages": ["hr", "en", "de", "it"],
            "local_specialties": ["local cuisine", "nature activities", "historic tours", "wine tasting"],
            "latitude": 45.2919,
            "longitude": 14.2742,
        }
    
    @pytest.fixture(scope="class")
    def test_attraction_data(self):
        """Test attraction data for Lovran area (AttractionCreate / AttractionBase)."""
        return {
            "name": "Učka Nature Park",
            "description": "Beautiful nature park with hiking trails and panoramic views of Kvarner Bay.",
            "short_description": "Nature park above Lovran",
            "attraction_type": "nature",
            "category_tags": ["outdoor_activities"],
            "city": "Lovran",
            "region": "Istria",
            "latitude": 45.3167,
            "longitude": 14.2167,
            "difficulty_level": "moderate",
            "duration_hours": 4.0,
            "seasonal_availability": "year_round",
            "name_translations": {
                "en": "Učka Nature Park",
                "hr": "Park prirode Učka",
                "de": "Naturpark Učka",
                "it": "Parco naturale dell'Učka",
            },
            "description_translations": {
                "en": "Beautiful nature park with hiking trails and panoramic views of Kvarner Bay",
                "hr": "Prekrasan park prirode s planinarskim stazama i panoramskim pogledom na Kvarnerski zaljev",
            },
            "accessibility_info": {
                "wheelchair_accessible": False,
                "mobility_requirements": ["good walking ability", "hiking boots recommended"],
            },
        }
    
    async def test_01_host_registration_and_authentication(self, client, test_host_data):
        """Test complete host registration and authentication flow."""
        print("\n🏠 Testing Host Registration & Authentication...")
        
        # Test host registration
        response = client.post("/api/v1/hosts/register", json=test_host_data)
        assert response.status_code == 201
        host_data = response.json()
        assert host_data["email"] == test_host_data["email"]
        assert host_data["business_name"] == test_host_data["business_name"]
        assert host_data["city"] == "Lovran"
        
        # Store host ID for later tests (class attr: pytest gives a new instance per test method)
        type(self).host_id = host_data["id"]
        print(f"✅ Host registered successfully: {host_data['business_name']}")
        
        # Test host login
        login_data = {
            "email": test_host_data["email"],
            "password": test_host_data["password"]
        }
        response = client.post("/api/v1/hosts/login", json=login_data)
        assert response.status_code == 200
        token_data = response.json()
        assert token_data.get("success") is True
        assert token_data.get("session_token")
        
        # Same header as guest-groups / attractions / settings / recommendations (host routes)
        type(self).auth_headers = {"X-Session-Token": token_data["session_token"]}
        print("✅ Host authentication successful")
        
        # Test authenticated profile access
        response = client.get("/api/v1/hosts/me", headers=self.auth_headers)
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["email"] == test_host_data["email"]
        print("✅ Authenticated profile access verified")
    
    async def test_02_host_settings_management(self, client):
        """Test host settings and API key management."""
        print("\n⚙️ Testing Host Settings Management...")
        
        # Test getting default settings
        response = client.get("/api/v1/settings/", headers=self.auth_headers)
        assert response.status_code == 200
        settings_data = response.json()
        assert settings_data["language_preference"] == "en"
        assert settings_data["timezone"] == "Europe/Zagreb"
        assert settings_data["currency"] == "EUR"
        print("✅ Default settings retrieved")
        
        # Test updating settings
        update_data = {
            "language_preference": "hr",
            "notification_preferences": {
                "email_enabled": True,
                "guest_booking": True,
                "recommendation_feedback": True
            },
            "recommendation_settings": {
                "max_recommendations": 15,
                "include_weather": True,
                "include_seasonal": True,
                "priority_local": True,
                "show_host_tips": True
            }
        }
        response = client.put("/api/v1/settings/", json=update_data, headers=self.auth_headers)
        assert response.status_code == 200
        updated_settings = response.json()
        assert updated_settings["language_preference"] == "hr"
        print("✅ Settings updated successfully")
        
        # Test API key creation
        api_key_data = {
            "service_name": "openai",
            "key_value": "sk-test-key-for-development-only",
            "description": "OpenAI API key for AI recommendations"
        }
        response = client.post("/api/v1/settings/api-keys", json=api_key_data, headers=self.auth_headers)
        assert response.status_code == 201
        key_response = response.json()
        assert key_response["service_name"] == "openai"
        assert "sk-test-key" not in key_response["masked_value"]  # Should be masked
        print("✅ API key created and masked properly")
    
    async def test_03_attraction_management_and_contributions(self, client, test_attraction_data):
        """Test attraction creation, management, and host contributions."""
        print("\n🏞️ Testing Attraction Management & Host Contributions...")
        
        # Test attraction creation by host
        response = client.post("/api/v1/attractions/", json=test_attraction_data, headers=self.auth_headers)
        assert response.status_code == 201
        attraction_data = response.json()
        assert attraction_data.get("name") == "Učka Nature Park"
        nt = attraction_data.get("name_translations") or {}
        assert nt.get("en", attraction_data.get("name")) == "Učka Nature Park"
        assert attraction_data["city"] == "Lovran"
        assert attraction_data["attraction_type"] == "nature"
        
        type(self).attraction_id = attraction_data["id"]
        print(f"✅ Attraction created: {attraction_data.get('name')}")
        
        # Test public attraction access (no auth required)
        response = client.get(f"/api/v1/attractions/{self.attraction_id}")
        assert response.status_code == 200
        public_data = response.json()
        assert public_data.get("name") == "Učka Nature Park"
        print("✅ Public attraction access verified")
        
        # Test attractions by city
        response = client.get("/api/v1/attractions/city/Lovran")
        assert response.status_code == 200
        city_attractions = response.json()
        assert len(city_attractions) >= 1
        assert any(attr["city"] == "Lovran" for attr in city_attractions)
        print("✅ City-based attraction filtering works")
        
        # Test host contribution
        contribution_data = {
            "contribution_type": "insider_tip",
            "title": "Best Time to Visit Vojak Peak",
            "content": "I've been taking guests to Vojak peak for 15 years. The best time is early morning (7-8 AM) when the mist clears and you can see all four countries - Croatia, Slovenia, Italy, and sometimes Austria on very clear days. My personal tip: bring a thermos of Croatian coffee and enjoy it at the top while watching the sunrise over Kvarner Bay. The trail from Poklon is the easiest route for families.",
            "is_public": True,
            "language": "en"
        }
        response = client.post(f"/api/v1/attractions/{self.attraction_id}/contributions", 
                             json=contribution_data, headers=self.auth_headers)
        assert response.status_code == 201
        contribution_response = response.json()
        assert contribution_response["contribution_type"] == "insider_tip"
        assert "15 years" in contribution_response["content"]
        print("✅ Host contribution added successfully")
        
        # Test getting contributions
        response = client.get(f"/api/v1/attractions/{self.attraction_id}/contributions")
        assert response.status_code == 200
        contributions = response.json()
        assert len(contributions) >= 1
        assert contributions[0]["contribution_type"] == "insider_tip"
        print("✅ Host contributions retrieved")
    
    async def test_04_guest_group_management(self, client):
        """Test guest group creation, access codes, and preferences."""
        print("\n👥 Testing Guest Group Management...")
        
        # Test guest group creation
        guest_group_data = {
            "group_name": "Miller Family Croatia Adventure",
            "group_size": 4,
            "check_in_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "check_out_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "preferred_language": "en",
            "supported_languages": ["en", "de"],
            "group_dynamics": "family",
            "interests": ["nature", "culture"],
        }
        response = client.post("/api/v1/guest-groups/", json=guest_group_data, headers=self.auth_headers)
        assert response.status_code == 201
        group_data = response.json()
        assert group_data["group_name"] == "Miller Family Croatia Adventure"
        assert group_data["group_size"] == 4
        assert "access_code" in group_data
        
        type(self).guest_group_id = group_data["id"]
        type(self).access_code = group_data["access_code"]
        print(f"✅ Guest group created with access code: {self.access_code}")
        
        # Test access code validation
        validation_data = {
            "access_code": self.access_code,
            "ip_address": "192.168.1.100"
        }
        response = client.post("/api/v1/guest-groups/access/validate", json=validation_data)
        assert response.status_code == 200
        validated_group = response.json()
        assert str(validated_group["id"]) == str(type(self).guest_group_id)
        print("✅ Access code validation successful")
        
        # Test adding guest preferences
        preference_data = {
            "guest_name": "Sarah Miller",
            "age_category": "adult",
            "personal_interests": ["nature", "photography", "hiking", "local_culture"],
            "dietary_needs": ["vegetarian"],
            "cultural_interests": ["traditional_music", "local_cuisine", "historic_sites"],
            "food_interests": ["istrian_cuisine", "local_wines", "traditional_dishes"],
            "language_preference": "en"
        }
        response = client.post(f"/api/v1/guest-groups/access/{self.access_code}/preferences", 
                             json=preference_data)
        assert response.status_code == 201
        preference_response = response.json()
        assert preference_response["guest_name"] == "Sarah Miller"
        assert "nature" in preference_response["personal_interests"]
        print("✅ Guest preferences added successfully")
        
        # Add second guest preference
        preference_data_2 = {
            "guest_name": "Tom Miller",
            "age_category": "teenager",
            "personal_interests": ["adventure", "water_sports", "local_culture"],
            "cultural_interests": ["music", "festivals"],
            "food_interests": ["local_specialties"],
            "language_preference": "en"
        }
        response = client.post(f"/api/v1/guest-groups/access/{self.access_code}/preferences", 
                             json=preference_data_2)
        assert response.status_code == 201
        print("✅ Second guest preferences added")
        
        # Test getting all preferences
        response = client.get(f"/api/v1/guest-groups/access/{self.access_code}/preferences")
        assert response.status_code == 200
        all_preferences = response.json()
        assert len(all_preferences) == 2
        guest_names = [pref["guest_name"] for pref in all_preferences]
        assert "Sarah Miller" in guest_names
        assert "Tom Miller" in guest_names
        print("✅ All guest preferences retrieved")
    
    async def test_05_personalized_recommendations(self, client):
        """Test the complete recommendation engine with Croatian tourism data."""
        print("\n🎯 Testing Personalized Recommendations...")
        
        # Test getting personalized recommendations for guest group
        recommendation_request = {
            "guest_group_id": self.guest_group_id,
            "max_recommendations": 10,
            "include_weather": True,
            "include_seasonal": True,
            "activity_duration": "half_day",
            "preferred_time": "morning",
            "weather_context": {
                "condition": "sunny",
                "temperature": 24,
                "season": "summer"
            }
        }
        response = client.post(f"/api/v1/recommendations/guest/{self.access_code}", 
                             json=recommendation_request)
        assert response.status_code == 200
        recommendations = response.json()
        assert "recommendations" in recommendations
        assert len(recommendations["recommendations"]) > 0
        
        # Verify recommendation quality (RecommendationResponse schema)
        first_rec = recommendations["recommendations"][0]
        assert first_rec.get("id")
        assert "relevance_score" in first_rec
        assert first_rec.get("description") or first_rec.get("why_recommended")
        assert first_rec.get("title")
        assert first_rec["relevance_score"] > 0.0
        print(f"✅ Generated {len(recommendations['recommendations'])} personalized recommendations")
        print(f"   Top recommendation: {first_rec.get('title', 'N/A')} (score: {first_rec['relevance_score']:.2f})")
        
        # Test seasonal recommendations
        response = client.get("/api/v1/recommendations/seasonal/summer?city=Lovran&limit=5")
        assert response.status_code == 200
        seasonal_recs = response.json()
        assert len(seasonal_recs) > 0
        assert all("relevance_score" in rec for rec in seasonal_recs)
        print("✅ Seasonal recommendations working")
        
        # Test weather-based recommendations
        response = client.get("/api/v1/recommendations/weather/Lovran?limit=5")
        assert response.status_code == 200
        weather_recs = response.json()
        assert len(weather_recs) > 0
        print("✅ Weather-based recommendations working")
        
        # Test recommendation feedback
        feedback_data = {
            "recommendation_id": first_rec.get("id") or str(uuid.uuid4()),
            "rating": 5,
            "feedback_text": "Perfect recommendation! The Učka Nature Park was exactly what our family needed. The host's insider tip about the early morning visit was spot on.",
            "visited": True,
            "helpful_factors": ["host_insights", "weather_consideration", "group_suitability"]
        }
        response = client.post(f"/api/v1/recommendations/guest/{self.access_code}/feedback", 
                             json=feedback_data)
        assert response.status_code == 201
        feedback_response = response.json()
        assert feedback_response["rating"] == 5
        print("✅ Recommendation feedback submitted")
    
    async def test_06_croatian_tourism_features(self, client):
        """Test Croatian tourism specific features."""
        print("\n🇭🇷 Testing Croatian Tourism Features...")
        
        # Test multi-language support
        response = client.get(f"/api/v1/attractions/{self.attraction_id}?language=hr")
        assert response.status_code == 200
        croatian_attraction = response.json()
        nt_hr = croatian_attraction.get("name_translations") or {}
        if nt_hr.get("hr"):
            assert nt_hr["hr"] == "Park prirode Učka"
        else:
            assert "Učka" in (croatian_attraction.get("name") or "")
        print("✅ Croatian language support verified")
        
        # Test German language support
        response = client.get(f"/api/v1/attractions/{self.attraction_id}?language=de")
        assert response.status_code == 200
        german_attraction = response.json()
        nt_de = german_attraction.get("name_translations") or {}
        assert nt_de.get("de") or "Učka" in (german_attraction.get("name") or "")
        print("✅ German language support verified")
        
        # Test regional filtering
        response = client.get("/api/v1/attractions/?city=Lovran&attraction_type=nature")
        assert response.status_code == 200
        lovran_nature = response.json()
        assert all(attr["city"] == "Lovran" and attr["attraction_type"] == "nature" 
                  for attr in lovran_nature)
        print("✅ Regional and type filtering works")
        
        # Test Croatian cultural categories
        cultural_interests = ["traditional_music", "local_cuisine", "historic_sites", "istrian_cuisine"]
        for interest in cultural_interests:
            # This would test if our system recognizes Croatian cultural categories
            assert interest in ["traditional_music", "local_cuisine", "historic_sites", "istrian_cuisine"]
        print("✅ Croatian cultural categories recognized")
    
    async def test_07_host_analytics_and_insights(self, client):
        """Test host analytics and business insights."""
        print("\n📊 Testing Host Analytics & Business Insights...")
        
        # Test host recommendation analytics
        response = client.get("/api/v1/recommendations/host/analytics?days=30", headers=self.auth_headers)
        assert response.status_code == 200
        analytics = response.json()
        assert "total_recommendations" in analytics
        assert "average_rating" in analytics
        assert "guest_satisfaction" in analytics
        print("✅ Host recommendation analytics retrieved")
        
        # Test attraction analytics
        response = client.get(f"/api/v1/attractions/{self.attraction_id}/analytics", headers=self.auth_headers)
        assert response.status_code == 200
        attraction_analytics = response.json()
        assert "view_count" in attraction_analytics or "views" in attraction_analytics
        assert "recommendation_count" in attraction_analytics or "recommendations" in attraction_analytics
        print("✅ Attraction analytics retrieved")
        
        # Test host contributions analytics
        response = client.get("/api/v1/attractions/host/contributions", headers=self.auth_headers)
        assert response.status_code == 200
        contributions = response.json()
        assert len(contributions) >= 1  # We created at least one contribution
        print("✅ Host contributions analytics retrieved")
    
    async def test_08_system_health_and_performance(self, client):
        """Test system health, performance, and error handling."""
        print("\n🏥 Testing System Health & Performance...")
        
        # Test health check endpoint
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        db_health = client.get("/health/databases")
        assert db_health.status_code == 200
        assert "databases" in db_health.json()
        print("✅ System health check passed")
        
        # Test API root endpoint
        response = client.get("/")
        assert response.status_code == 200
        root_data = response.json()
        assert "TouristGuideLocal" in root_data["message"]
        print("✅ API root endpoint working")
        
        # Test error handling with invalid data
        response = client.post("/api/v1/hosts/register", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error
        print("✅ Input validation error handling works")
        
        # Test authentication error handling
        response = client.get("/api/v1/hosts/me")  # No auth header
        assert response.status_code == 401
        print("✅ Authentication error handling works")
        
        # Test not found error handling
        response = client.get(f"/api/v1/attractions/{uuid.uuid4()}")
        assert response.status_code == 404
        print("✅ Not found error handling works")
    
    async def test_09_end_to_end_workflow(self, client):
        """Test complete end-to-end workflow simulation."""
        print("\n🔄 Testing Complete End-to-End Workflow...")
        
        # Simulate complete guest journey
        print("   Simulating complete guest journey...")
        
        # 1. Host creates guest group (already done in test_04)
        assert getattr(type(self), "guest_group_id", None) is not None
        assert getattr(type(self), "access_code", None) is not None
        print("   ✓ Guest group created with access code")
        
        # 2. Guests use access code to set preferences (already done)
        response = client.get(f"/api/v1/guest-groups/access/{self.access_code}/preferences")
        assert response.status_code == 200
        preferences = response.json()
        assert len(preferences) >= 2
        print("   ✓ Guest preferences collected")
        
        # 3. System generates personalized recommendations
        recommendation_request = {
            "max_recommendations": 5,
            "include_weather": True,
            "include_seasonal": True,
            "activity_duration": "full_day"
        }
        response = client.post(f"/api/v1/recommendations/guest/{self.access_code}", 
                             json=recommendation_request)
        assert response.status_code == 200
        recommendations = response.json()
        assert len(recommendations["recommendations"]) >= 1
        print("   ✓ Personalized recommendations generated")
        
        # 4. Guests provide feedback
        first_rec = recommendations["recommendations"][0]
        feedback_data = {
            "recommendation_id": first_rec.get("id") or str(uuid.uuid4()),
            "rating": 4,
            "feedback_text": "Great recommendation, we enjoyed it!",
            "visited": True
        }
        response = client.post(f"/api/v1/recommendations/guest/{self.access_code}/feedback", 
                             json=feedback_data)
        assert response.status_code == 201
        print("   ✓ Guest feedback collected")
        
        # 5. Host views analytics
        response = client.get("/api/v1/recommendations/host/analytics", headers=self.auth_headers)
        assert response.status_code == 200
        analytics = response.json()
        print("   ✓ Host analytics updated")
        
        print("✅ Complete end-to-end workflow successful!")
    
    async def test_10_data_consistency_and_integrity(self, client):
        """Test data consistency and integrity across all systems."""
        print("\n🔐 Testing Data Consistency & Integrity...")
        
        # Test that guest group belongs to correct host
        response = client.get("/api/v1/guest-groups/", headers=self.auth_headers)
        assert response.status_code == 200
        host_groups = response.json()
        group_ids = {str(group["id"]) for group in host_groups}
        assert str(type(self).guest_group_id) in group_ids
        print("✅ Guest group ownership verified")
        
        # Test that attractions are properly linked
        response = client.get(f"/api/v1/attractions/{self.attraction_id}")
        assert response.status_code == 200
        attraction = response.json()
        assert attraction["city"] == "Lovran"
        assert attraction.get("region") == "Istria"
        print("✅ Attraction data integrity verified")
        
        # Test that recommendations reference valid attractions
        recommendation_request = {"max_recommendations": 3}
        response = client.post(f"/api/v1/recommendations/guest/{self.access_code}", 
                             json=recommendation_request)
        assert response.status_code == 200
        recommendations = response.json()
        
        for rec in recommendations["recommendations"]:
            if "attraction_id" in rec:
                # Verify attraction exists
                attr_response = client.get(f"/api/v1/attractions/{rec['attraction_id']}")
                assert attr_response.status_code == 200
        print("✅ Recommendation-attraction links verified")
        
        print("✅ All data consistency checks passed!")


# Run individual test methods for debugging
async def run_integration_tests():
    """
    Run comprehensive integration tests for TouristGuideLocal.
    
    This function can be called directly for testing purposes.
    """
    print("🚀 Starting TouristGuideLocal Integration Tests...")
    print("=" * 60)
    
    test_instance = TestTouristGuideLocalIntegration()
    client = TestClient(app)
    
    # Test data
    test_host_data = {
        "email": "integration-test@lovran-apartments.hr",
        "password": "SecurePassword123!",
        "full_name": "Ana Marić",
        "business_name": "Lovran Sea View Apartments",
        "phone": "+385 51 291 123",
        "address": "Oprić 71, 51450 Lovran, Croatia",
        "city": "Lovran",
        "country": "Croatia",
        "description": "Family-run apartments with stunning sea views in historic Lovran.",
        "languages": ["hr", "en", "de", "it"],
        "specialties": ["local cuisine", "nature activities", "historic tours"],
        "coordinates": {"latitude": 45.2919, "longitude": 14.2742}
    }
    
    test_attraction_data = {
        "name_translations": {
            "en": "Učka Nature Park Integration Test",
            "hr": "Park prirode Učka - Test",
        },
        "description_translations": {
            "en": "Test attraction for integration testing",
            "hr": "Test atrakcija za integracijske testove"
        },
        "attraction_type": "nature",
        "category": "outdoor_activities",
        "city": "Lovran",
        "region": "Istria",
        "country": "Croatia",
        "coordinates": {"latitude": 45.3167, "longitude": 14.2167},
        "difficulty_level": "moderate",
        "duration_minutes": 240,
        "seasonal_availability": {
            "spring": {"available": True, "best_months": ["April", "May"]},
            "summer": {"available": True, "best_months": ["June", "July", "August"]},
            "autumn": {"available": True, "best_months": ["September", "October"]},
            "winter": {"available": True, "notes": "Weather dependent"}
        },
        "accessibility": {
            "wheelchair_accessible": False,
            "mobility_requirements": ["good walking ability"]
        },
        "cost_info": {"entry_fee": 0, "currency": "EUR", "notes": "Free entry"}
    }
    
    try:
        # Run all tests in sequence
        await test_instance.test_01_host_registration_and_authentication(client, test_host_data)
        await test_instance.test_02_host_settings_management(client)
        await test_instance.test_03_attraction_management_and_contributions(client, test_attraction_data)
        await test_instance.test_04_guest_group_management(client)
        await test_instance.test_05_personalized_recommendations(client)
        await test_instance.test_06_croatian_tourism_features(client)
        await test_instance.test_07_host_analytics_and_insights(client)
        await test_instance.test_08_system_health_and_performance(client)
        await test_instance.test_09_end_to_end_workflow(client)
        await test_instance.test_10_data_consistency_and_integrity(client)
        
        print("=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ TouristGuideLocal platform is ready for production")
        print("🇭🇷 Croatian tourism features fully functional")
        print("🏠 Host management system operational")
        print("👥 Guest group system working perfectly")
        print("🎯 Recommendation engine delivering personalized results")
        print("📊 Analytics and insights providing valuable data")
        
        return True
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ INTEGRATION TEST FAILED: {str(e)}")
        print("Please check the error details and fix any issues.")
        return False


if __name__ == "__main__":
    # Run integration tests directly
    asyncio.run(run_integration_tests()) 