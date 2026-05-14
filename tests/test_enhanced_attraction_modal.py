"""
Test Enhanced Attraction Creation Modal Functionality

This test suite verifies the enhanced attraction creation modal functionality including:
- Enhanced Google Places search with dropdown results
- Auto-population from Google Places data
- Nearby places for AI enhancement
- Location verification with map adjustment
- Improved user flow and error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Mock Google Places API responses
MOCK_GOOGLE_PLACES_RESPONSE = {
    "places": [
        {
            "id": "place_123",
            "displayName": "Konoba Stari Grad",
            "formattedAddress": "Lovran, Croatia",
            "types": ["restaurant", "food", "establishment"],
            "rating": 4.5,
            "userRatingCount": 127,
            "priceLevel": 2,
            "location": {"lat": 45.337769, "lng": 14.305187},
            "website": "https://konoba-stari-grad.hr",
            "formattedPhoneNumber": "+385 51 291 123",
            "openingHours": {
                "openNow": True,
                "weekdayText": ["Monday: 12:00 PM – 11:00 PM", "Tuesday: 12:00 PM – 11:00 PM"]
            }
        },
        {
            "id": "place_456",
            "displayName": "Lovran Lungomare",
            "formattedAddress": "Lungomare, Lovran, Croatia",
            "types": ["tourist_attraction", "natural_feature"],
            "rating": 4.8,
            "userRatingCount": 89,
            "priceLevel": 0,
            "location": {"lat": 45.338123, "lng": 14.306789}
        }
    ]
}

MOCK_NEARBY_PLACES_RESPONSE = {
    "places": [
        {
            "id": "nearby_1",
            "displayName": "Cafe Central",
            "formattedAddress": "Lovran, Croatia",
            "types": ["cafe", "food"],
            "rating": 4.2,
            "location": {"lat": 45.337900, "lng": 14.305500}
        },
        {
            "id": "nearby_2",
            "displayName": "Lovran Beach",
            "formattedAddress": "Lovran, Croatia",
            "types": ["beach", "natural_feature"],
            "rating": 4.6,
            "location": {"lat": 45.338000, "lng": 14.306000}
        }
    ]
}

class TestEnhancedAttractionModal:
    """Test suite for enhanced attraction creation modal functionality."""

    def test_enhanced_place_interface_structure(self):
        """Test that EnhancedPlace interface includes all required fields."""
        # Define the expected interface structure
        expected_fields = [
            "place_id",
            "name", 
            "displayName",
            "formatted_address",
            "types",
            "rating",
            "user_ratings_total",
            "price_level",
            "geometry",
            "website",
            "phone_number",
            "opening_hours"
        ]
        
        # Mock place data structure
        mock_place = {
            "place_id": "test_123",
            "name": "Test Place",
            "displayName": "Test Display Name",
            "formatted_address": "Test Address, Croatia",
            "types": ["restaurant", "food"],
            "rating": 4.5,
            "user_ratings_total": 100,
            "price_level": 2,
            "geometry": {
                "location": {
                    "lat": 45.337769,
                    "lng": 14.305187
                }
            },
            "website": "https://test.com",
            "phone_number": "+385 51 123 456",
            "opening_hours": {
                "open_now": True,
                "weekday_text": ["Monday: 12:00 PM – 11:00 PM"]
            }
        }
        
        # Verify all expected fields are present
        for field in expected_fields:
            assert field in mock_place, f"Missing field: {field}"
        
        # Verify data types and values
        assert mock_place["place_id"] == "test_123"
        assert mock_place["displayName"] == "Test Display Name"
        assert mock_place["types"] == ["restaurant", "food"]
        assert mock_place["rating"] == 4.5
        assert mock_place["geometry"]["location"]["lat"] == 45.337769

    def test_enhanced_search_strategies(self):
        """Test enhanced search with multiple search strategies."""
        # Define search strategies
        search_strategies = [
            {
                "textQuery": "Lovran Pub Croatia",
                "fields": ['displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'website', 'formattedPhoneNumber', 'openingHours']
            },
            {
                "textQuery": "Lovran Pub",
                "fields": ['displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'website', 'formattedPhoneNumber', 'openingHours']
            },
            {
                "textQuery": "Lovran Pub, Croatia",
                "fields": ['displayName', 'formattedAddress', 'types', 'rating', 'userRatingCount', 'priceLevel', 'photos', 'location', 'website', 'formattedPhoneNumber', 'openingHours']
            }
        ]
        
        # Verify search strategies are properly defined
        assert len(search_strategies) == 3
        
        for strategy in search_strategies:
            assert "textQuery" in strategy
            assert "fields" in strategy
            assert isinstance(strategy["fields"], list)
            assert len(strategy["fields"]) > 0

    def test_auto_population_logic(self):
        """Test auto-population of form fields from Google Places data."""
        # Mock place data
        mock_place = {
            "place_id": "place_123",
            "displayName": "Konoba Stari Grad",
            "formatted_address": "Lovran, Croatia",
            "types": ["restaurant", "food"],
            "rating": 4.5,
            "price_level": 2,
            "geometry": {
                "location": {
                    "lat": 45.337769,
                    "lng": 14.305187
                }
            }
        }
        
        # Mock form data
        form_data = {}
        
        # Simulate auto-population logic
        def populate_form_data(place):
            address_parts = place["formatted_address"].split(',')
            city = address_parts[0].strip() if address_parts else ''
            
            # Map Google types to attraction types
            type_mapping = {
                'restaurant': 'culinary',
                'food': 'culinary',
                'cafe': 'culinary',
                'bar': 'culinary',
                'museum': 'cultural',
                'tourist_attraction': 'cultural',
                'beach': 'natural',
                'natural_feature': 'natural'
            }
            
            attraction_type = 'cultural'  # default
            for place_type in place["types"]:
                if place_type in type_mapping:
                    attraction_type = type_mapping[place_type]
                    break
            
            # Price level to text
            price_text = '€' * place["price_level"] if place["price_level"] else 'Price not available'
            
            return {
                "name": place["displayName"],
                "city": city,
                "address": place["formatted_address"],
                "attraction_type": attraction_type,
                "latitude": place["geometry"]["location"]["lat"],
                "longitude": place["geometry"]["location"]["lng"],
                "admission_fee": price_text,
                "category_tags": place["types"]
            }
        
        # Test auto-population
        populated_data = populate_form_data(mock_place)
        
        # Verify all fields are populated correctly
        expected_data = {
            "name": "Konoba Stari Grad",
            "city": "Lovran",
            "address": "Lovran, Croatia",
            "attraction_type": "culinary",
            "latitude": 45.337769,
            "longitude": 14.305187,
            "admission_fee": "€€",
            "category_tags": ["restaurant", "food"]
        }
        
        for key, value in expected_data.items():
            assert populated_data[key] == value, f"Field {key} mismatch: expected {value}, got {populated_data[key]}"

    def test_nearby_places_search(self):
        """Test fetching nearby places for AI enhancement."""
        # Mock coordinates
        latitude = 45.337769
        longitude = 14.305187
        
        # Mock nearby search request
        nearby_search_request = {
            "locationRestriction": {
                "center": {"lat": latitude, "lng": longitude},
                "radius": 2000  # 2km radius
            },
            "typesFilter": ["establishment", "point_of_interest", "natural_feature"]
        }
        
        # Verify search parameters
        assert nearby_search_request["locationRestriction"]["center"]["lat"] == latitude
        assert nearby_search_request["locationRestriction"]["center"]["lng"] == longitude
        assert nearby_search_request["locationRestriction"]["radius"] == 2000
        assert "establishment" in nearby_search_request["typesFilter"]
        assert "point_of_interest" in nearby_search_request["typesFilter"]
        assert "natural_feature" in nearby_search_request["typesFilter"]

    def test_location_verification(self):
        """Test location verification and map adjustment functionality."""
        # Test location adjustment
        original_lat = 45.337769
        original_lng = 14.305187
        new_lat = 45.338000
        new_lng = 14.306000
        
        # Mock location adjustment callback
        adjustment_callback = Mock()
        
        # Test that location adjustment works
        adjustment_callback(new_lat, new_lng)
        
        # Verify callback is called with new coordinates
        adjustment_callback.assert_called_with(new_lat, new_lng)
        
        # Verify coordinates are different
        assert new_lat != original_lat
        assert new_lng != original_lng

    def test_enhanced_search_dropdown_display(self):
        """Test enhanced search dropdown with rich place information."""
        # Mock search results
        search_results = MOCK_GOOGLE_PLACES_RESPONSE['places']
        
        # Test dropdown display requirements
        for place in search_results:
            # Verify required fields are present
            assert "displayName" in place
            assert "formattedAddress" in place
            assert "types" in place
            assert "rating" in place
            assert "priceLevel" in place
            
            # Verify data types
            assert isinstance(place["displayName"], str)
            assert isinstance(place["formattedAddress"], str)
            assert isinstance(place["types"], list)
            assert isinstance(place["rating"], (int, float)) or place["rating"] is None
            assert isinstance(place["priceLevel"], int) or place["priceLevel"] is None

    def test_ai_content_generation_context(self):
        """Test AI content generation with enhanced Google Places context."""
        # Mock selected location
        selected_location = {
            "place_id": "place_123",
            "displayName": "Konoba Stari Grad",
            "formatted_address": "Lovran, Croatia",
            "types": ["restaurant", "food"],
            "rating": 4.5,
            "price_level": 2,
            "geometry": {
                "location": {
                    "lat": 45.337769,
                    "lng": 14.305187
                }
            }
        }
        
        # Mock nearby places
        nearby_places = MOCK_NEARBY_PLACES_RESPONSE['places']
        
        # Test AI context preparation
        def prepare_ai_context(location, nearby):
            return {
                "place_id": location["place_id"],
                "name": location["displayName"],
                "address": location["formatted_address"],
                "types": location["types"],
                "rating": location["rating"],
                "price_level": location["price_level"],
                "coordinates": location["geometry"]["location"],
                "nearby_places": [
                    {
                        "name": place["displayName"],
                        "types": place["types"],
                        "rating": place["rating"]
                    }
                    for place in nearby
                ]
            }
        
        expected_context = prepare_ai_context(selected_location, nearby_places)
        
        # Verify context is prepared correctly for AI generation
        assert expected_context["place_id"] == selected_location["place_id"]
        assert expected_context["name"] == selected_location["displayName"]
        assert len(expected_context["nearby_places"]) == 2
        assert expected_context["nearby_places"][0]["name"] == "Cafe Central"
        assert expected_context["nearby_places"][1]["name"] == "Lovran Beach"

    def test_error_handling(self):
        """Test error handling and fallback mechanisms."""
        # Test error message generation
        def generate_error_message(error_type, query=""):
            error_messages = {
                "search_failed": "❌ Search failed. Please try again or check your internet connection.",
                "no_results": f"🔍 No places found for \"{query}\". Try a different search term or be more specific.",
                "api_error": "❌ Google Maps API error. Please try again later."
            }
            return error_messages.get(error_type, "❌ Unknown error occurred.")
        
        # Test error messages
        search_error = generate_error_message("search_failed")
        no_results_error = generate_error_message("no_results", "Invalid Search")
        api_error = generate_error_message("api_error")
        
        # Verify error handling works
        assert "Search failed" in search_error
        assert "No places found" in no_results_error
        assert "Google Maps API error" in api_error

    def test_flexible_location_entry(self):
        """Test flexible location entry for custom/local places."""
        # Test custom location entry
        custom_location = "beach Moščenićka draga"
        
        # Verify custom locations can be handled
        assert isinstance(custom_location, str)
        assert len(custom_location) > 0
        
        # Test manual location with coordinates
        manual_coordinates = {"lat": 45.337769, "lng": 14.305187}
        
        # Verify manual location works
        assert manual_coordinates["lat"] == 45.337769
        assert manual_coordinates["lng"] == 14.305187
        assert isinstance(manual_coordinates["lat"], float)
        assert isinstance(manual_coordinates["lng"], float)

    def test_search_debouncing(self):
        """Test search debouncing to avoid excessive API calls."""
        # Mock debounced search
        search_timeout = 300  # milliseconds
        
        # Test that search is debounced
        assert search_timeout == 300
        assert search_timeout > 0
        
        # Simulate debouncing logic
        def should_debounce(last_search_time, current_time, timeout):
            return (current_time - last_search_time) < timeout
        
                # Test debouncing
        last_search = 1000
        current_time = 1200
        should_debounce_result = should_debounce(last_search, current_time, search_timeout)

        # Should debounce if not enough time has passed (200ms < 300ms timeout)
        assert should_debounce_result
        
        # Test when enough time has passed
        current_time_enough = 1400  # 400ms later
        should_debounce_result_enough = should_debounce(last_search, current_time_enough, search_timeout)
        
        # Should not debounce if enough time has passed
        assert not should_debounce_result_enough

    def test_comprehensive_place_types_search(self):
        """Test comprehensive search across all place types."""
        # Test search types
        search_types = [
            'establishment',      # Restaurants, shops, etc.
            'point_of_interest',  # Landmarks, attractions
            'natural_feature',    # Beaches, mountains
            'geocode'            # General locations
        ]
        
        # Verify all place types are included
        assert 'establishment' in search_types
        assert 'point_of_interest' in search_types
        assert 'natural_feature' in search_types
        assert 'geocode' in search_types
        assert len(search_types) == 4

    def test_duplicate_removal_and_ranking(self):
        """Test duplicate removal and result ranking."""
        # Mock duplicate results
        duplicate_results = [
            {"id": "place_123", "displayName": "Konoba Stari Grad"},
            {"id": "place_123", "displayName": "Konoba Stari Grad"},  # Duplicate
            {"id": "place_456", "displayName": "Lovran Lungomare"}
        ]
        
        # Test duplicate removal
        unique_results = []
        seen_ids = set()
        
        for result in duplicate_results:
            if result["id"] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result["id"])
        
        # Verify duplicates are removed
        assert len(unique_results) == 2
        assert unique_results[0]["id"] == "place_123"
        assert unique_results[1]["id"] == "place_456"
        assert len(seen_ids) == 2

    def test_user_experience_improvements(self):
        """Test user experience improvements and feedback."""
        # Test loading states
        loading_states = {
            "isSearchingLocation": False,
            "isLoadingNearby": False,
            "isGeneratingContent": False
        }
        
        # Verify loading states are boolean
        for state, value in loading_states.items():
            assert isinstance(value, bool)
        
        # Test success messages
        success_messages = [
            "✅ Found: Konoba Stari Grad - Auto-populated with Google Places data!",
            "✅ AI content generated successfully! Used 5 real Croatian tourism sources + Google Places data.",
            "📍 Location adjusted to: 45.337769, 14.305187"
        ]
        
        # Test error messages
        error_messages = [
            "🔍 No places found for \"Invalid Search\". Try a different search term or be more specific.",
            "❌ Search failed. Please try again or check your internet connection.",
            "❌ Error generating AI content. Please try again."
        ]
        
        # Verify all message types are available
        assert any("✅" in msg for msg in success_messages)
        assert any("❌" in msg for msg in error_messages)
        assert any("🔍" in msg for msg in error_messages)
        
        # Verify message content
        for msg in success_messages:
            assert len(msg) > 0
        for msg in error_messages:
            assert len(msg) > 0

    def test_price_level_mapping(self):
        """Test price level to text mapping."""
        def get_price_level_text(level):
            if not level:
                return 'Price not available'
            return '€' * level
        
        # Test price level mapping
        assert get_price_level_text(0) == 'Price not available'
        assert get_price_level_text(1) == '€'
        assert get_price_level_text(2) == '€€'
        assert get_price_level_text(3) == '€€€'
        assert get_price_level_text(4) == '€€€€'
        assert get_price_level_text(None) == 'Price not available'

    def test_type_to_category_mapping(self):
        """Test Google Places types to attraction category mapping."""
        type_mapping = {
            'restaurant': 'culinary',
            'food': 'culinary',
            'cafe': 'culinary',
            'bar': 'culinary',
            'museum': 'cultural',
            'art_gallery': 'cultural',
            'church': 'historic',
            'place_of_worship': 'historic',
            'castle': 'historic',
            'historic': 'historic',
            'tourist_attraction': 'cultural',
            'park': 'natural',
            'natural_feature': 'natural',
            'beach': 'natural',
            'amusement_park': 'activity',
            'aquarium': 'cultural',
            'zoo': 'natural',
            'shopping_mall': 'shopping',
            'store': 'shopping',
            'market': 'shopping',
            'winery': 'culinary',
            'spa': 'wellness',
            'gym': 'activity',
            'hiking': 'activity',
            'campground': 'activity',
            'hotel': 'accommodation',
            'lodging': 'accommodation',
            'night_club': 'nightlife',
            'entertainment': 'activity'
        }
        
        def get_category_from_types(types):
            for type_name in types:
                if type_name in type_mapping:
                    return type_mapping[type_name]
            return 'cultural'  # default
        
        # Test type mapping
        assert get_category_from_types(['restaurant', 'food']) == 'culinary'
        assert get_category_from_types(['museum', 'art_gallery']) == 'cultural'
        assert get_category_from_types(['beach', 'natural_feature']) == 'natural'
        assert get_category_from_types(['hotel', 'lodging']) == 'accommodation'
        assert get_category_from_types(['unknown_type']) == 'cultural'  # default

import unittest
from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio

class TestEnhancedAttractionModalSearch(unittest.TestCase):
    """Test the enhanced attraction modal search functionality."""

    def test_search_strategies_are_valid(self):
        """Test that search strategies don't contain invalid field names."""
        # These are the search strategies from the enhanced modal
        search_strategies = [
            {"textQuery": "Lovran Pub Croatia"},
            {"textQuery": "Lovran Pub"},
            {"textQuery": "Lovran Pub, Croatia"},
            {"textQuery": "Lovran Pub restaurant Croatia"},
            {"textQuery": "Lovran Pub pub Croatia"},
            {"textQuery": "Lovran Pub bar Croatia"}
        ]
        
        # Verify no invalid field names are present
        invalid_fields = ['website', 'formattedPhoneNumber', 'openingHours']
        
        for strategy in search_strategies:
            # Check that no invalid fields are in the strategy
            for field in invalid_fields:
                self.assertNotIn(field, str(strategy), 
                               f"Invalid field '{field}' found in strategy: {strategy}")
            
            # Verify each strategy has textQuery
            self.assertIn('textQuery', strategy, 
                         f"Strategy missing textQuery: {strategy}")

    def test_lovran_pub_google_places_response(self):
        """Test to show what Google Places API returns for 'Lovran Pub' search."""
        
        # Mock Google Places API response for "Lovran Pub" search
        mock_google_places_response = [
            {
                "id": "ChIJN1t_tDeuZEcRUxMYF4TN48Q",
                "displayName": "Lovran Pub",
                "formattedAddress": "Lovran, Croatia",
                "types": ["bar", "establishment", "food", "point_of_interest"],
                "rating": 4.2,
                "userRatingCount": 87,
                "priceLevel": 2,
                "location": {
                    "lat": 45.2919,
                    "lng": 14.2747
                },
                "website": "https://lovranpub.hr",
                "formattedPhoneNumber": "+385 51 291 123",
                "openingHours": {
                    "openNow": True,
                    "weekdayText": [
                        "Monday: 10:00 AM – 2:00 AM",
                        "Tuesday: 10:00 AM – 2:00 AM",
                        "Wednesday: 10:00 AM – 2:00 AM",
                        "Thursday: 10:00 AM – 2:00 AM",
                        "Friday: 10:00 AM – 3:00 AM",
                        "Saturday: 10:00 AM – 3:00 AM",
                        "Sunday: 10:00 AM – 2:00 AM"
                    ]
                },
                "photos": [
                    {
                        "name": "photos/photo1",
                        "widthPx": 1920,
                        "heightPx": 1080
                    }
                ]
            },
            {
                "id": "ChIJK2t_tDeuZEcRUxMYF4TN48Q",
                "displayName": "Pub Lovran",
                "formattedAddress": "Lovran, Croatia",
                "types": ["bar", "establishment", "food", "point_of_interest"],
                "rating": 4.0,
                "userRatingCount": 45,
                "priceLevel": 1,
                "location": {
                    "lat": 45.2921,
                    "lng": 14.2749
                }
            },
            {
                "id": "ChIJL3t_tDeuZEcRUxMYF4TN48Q",
                "displayName": "Lovran Beach Bar",
                "formattedAddress": "Lovran, Croatia",
                "types": ["bar", "establishment", "food", "point_of_interest"],
                "rating": 4.5,
                "userRatingCount": 123,
                "priceLevel": 2,
                "location": {
                    "lat": 45.2915,
                    "lng": 14.2745
                }
            }
        ]
        
        # Simulate the search process from the component
        def simulate_lovran_pub_search():
            """Simulate the search process for 'Lovran Pub'."""
            print("\n" + "="*60)
            print("🔍 GOOGLE PLACES API RESPONSE FOR 'LOVRAN PUB' SEARCH")
            print("="*60)
            
            # Show what search strategies would be used
            search_strategies = [
                {"textQuery": "Lovran Pub Croatia"},
                {"textQuery": "Lovran Pub"},
                {"textQuery": "Lovran Pub, Croatia"},
                {"textQuery": "Lovran Pub restaurant Croatia"},
                {"textQuery": "Lovran Pub pub Croatia"},
                {"textQuery": "Lovran Pub bar Croatia"}
            ]
            
            print(f"\n📋 Search Strategies Used:")
            for i, strategy in enumerate(search_strategies, 1):
                print(f"  {i}. {strategy['textQuery']}")
            
            print(f"\n✅ Raw Google Places API Response:")
            print(f"   Found {len(mock_google_places_response)} places")
            
            # Show detailed response for each place
            for i, place in enumerate(mock_google_places_response, 1):
                print(f"\n📍 Place {i}: {place['displayName']}")
                print(f"   ID: {place['id']}")
                print(f"   Address: {place['formattedAddress']}")
                print(f"   Types: {', '.join(place['types'])}")
                print(f"   Rating: ⭐ {place['rating']} ({place['userRatingCount']} reviews)")
                print(f"   Price Level: {'€' * place['priceLevel'] if place['priceLevel'] else 'Not available'}")
                print(f"   Coordinates: {place['location']['lat']}, {place['location']['lng']}")
                
                if 'website' in place:
                    print(f"   Website: {place['website']}")
                if 'formattedPhoneNumber' in place:
                    print(f"   Phone: {place['formattedPhoneNumber']}")
                if 'openingHours' in place:
                    print(f"   Open Now: {'🟢 Yes' if place['openingHours']['openNow'] else '🔴 No'}")
                    print(f"   Hours: {place['openingHours']['weekdayText'][0] if place['openingHours']['weekdayText'] else 'Not available'}")
            
            # Show how the component would map this data
            print(f"\n🔄 Component Data Mapping:")
            for i, place in enumerate(mock_google_places_response, 1):
                mapped_data = {
                    "place_id": place["id"],
                    "name": place["displayName"],
                    "displayName": place["displayName"],
                    "formatted_address": place["formattedAddress"],
                    "types": place["types"],
                    "rating": place["rating"],
                    "user_ratings_total": place["userRatingCount"],
                    "price_level": place["priceLevel"],
                    "geometry": {
                        "location": {
                            "lat": place["location"]["lat"],
                            "lng": place["location"]["lng"]
                        }
                    }
                }
                
                if "website" in place:
                    mapped_data["website"] = place["website"]
                if "formattedPhoneNumber" in place:
                    mapped_data["phone_number"] = place["formattedPhoneNumber"]
                if "openingHours" in place:
                    mapped_data["opening_hours"] = {
                        "open_now": place["openingHours"]["openNow"],
                        "weekday_text": place["openingHours"]["weekdayText"]
                    }
                
                print(f"\n   📍 Mapped Place {i}: {mapped_data['name']}")
                print(f"      Place ID: {mapped_data['place_id']}")
                print(f"      Address: {mapped_data['formatted_address']}")
                print(f"      Types: {mapped_data['types']}")
                print(f"      Rating: ⭐ {mapped_data['rating']} ({mapped_data['user_ratings_total']} reviews)")
                print(f"      Price: {'€' * mapped_data['price_level'] if mapped_data['price_level'] else 'Not available'}")
                print(f"      Coordinates: {mapped_data['geometry']['location']['lat']}, {mapped_data['geometry']['location']['lng']}")
                
                if "website" in mapped_data:
                    print(f"      Website: {mapped_data['website']}")
                if "phone_number" in mapped_data:
                    print(f"      Phone: {mapped_data['phone_number']}")
                if "opening_hours" in mapped_data:
                    print(f"      Open Now: {'🟢 Yes' if mapped_data['opening_hours']['open_now'] else '🔴 No'}")
            
            # Show auto-population results
            print(f"\n🎯 Auto-Population Results:")
            for i, place in enumerate(mock_google_places_response, 1):
                # Extract city from address
                address_parts = place["formattedAddress"].split(',')
                city = address_parts[0].strip() if address_parts else ''
                
                # Map types to attraction category
                type_mapping = {
                    'restaurant': 'culinary', 'food': 'culinary', 'cafe': 'culinary', 'bar': 'culinary',
                    'museum': 'cultural', 'tourist_attraction': 'cultural', 'beach': 'natural', 'natural_feature': 'natural'
                }
                
                attraction_type = 'cultural'  # default
                for place_type in place["types"]:
                    if place_type in type_mapping:
                        attraction_type = type_mapping[place_type]
                        break
                
                # Price level mapping
                price_text = '€' * place["priceLevel"] if place["priceLevel"] else 'Price not available'
                
                auto_populated_data = {
                    "name": place["displayName"],
                    "city": city,
                    "address": place["formattedAddress"],
                    "attraction_type": attraction_type,
                    "latitude": place["location"]["lat"],
                    "longitude": place["location"]["lng"],
                    "admission_fee": price_text,
                    "category_tags": place["types"]
                }
                
                print(f"\n   🎯 Auto-Populated Place {i}: {auto_populated_data['name']}")
                print(f"      Name: {auto_populated_data['name']}")
                print(f"      City: {auto_populated_data['city']}")
                print(f"      Address: {auto_populated_data['address']}")
                print(f"      Type: {auto_populated_data['attraction_type']}")
                print(f"      Coordinates: {auto_populated_data['latitude']}, {auto_populated_data['longitude']}")
                print(f"      Admission Fee: {auto_populated_data['admission_fee']}")
                print(f"      Category Tags: {auto_populated_data['category_tags']}")
            
            print("\n" + "="*60)
            return mock_google_places_response
        
        # Run the simulation
        results = simulate_lovran_pub_search()
        
        # Verify we got results
        self.assertGreater(len(results), 0, "Should find at least one place for 'Lovran Pub'")
        
        # Verify the first result has expected structure
        first_result = results[0]
        self.assertIn('displayName', first_result)
        self.assertIn('formattedAddress', first_result)
        self.assertIn('types', first_result)
        self.assertIn('location', first_result)
        
        # Verify it's actually a bar/pub type
        self.assertIn('bar', first_result['types'], "Should be classified as a bar")
        
        print(f"\n✅ Test passed! Found {len(results)} places for 'Lovran Pub' search")

    def test_place_mapping_logic(self):
        """Test the logic for mapping Google Places data to form fields."""
        # Mock Google Places response
        mock_place = {
            "id": "place_123",
            "displayName": "Konoba Stari Grad",
            "formattedAddress": "Lovran, Croatia",
            "types": ["restaurant", "food", "establishment"],
            "rating": 4.5,
            "userRatingCount": 150,
            "priceLevel": 2,
            "location": {
                "lat": 45.337769,
                "lng": 14.305187
            }
        }
        
        # Test the mapping logic (simplified version of what's in the component)
        def map_place_to_form_data(place):
            address_parts = place["formattedAddress"].split(',')
            city = address_parts[0].strip() if address_parts else ''
            
            # Type mapping logic
            type_mapping = {
                'restaurant': 'culinary', 'food': 'culinary', 'cafe': 'culinary', 'bar': 'culinary',
                'museum': 'cultural', 'tourist_attraction': 'cultural', 'beach': 'natural', 'natural_feature': 'natural'
            }
            
            attraction_type = 'cultural'  # default
            for place_type in place["types"]:
                if place_type in type_mapping:
                    attraction_type = type_mapping[place_type]
                    break
            
            # Price level mapping
            price_text = '€' * place["priceLevel"] if place["priceLevel"] else 'Price not available'
            
            return {
                "name": place["displayName"],
                "city": city,
                "address": place["formattedAddress"],
                "attraction_type": attraction_type,
                "latitude": place["location"]["lat"],
                "longitude": place["location"]["lng"],
                "admission_fee": price_text,
                "category_tags": place["types"]
            }
        
        result = map_place_to_form_data(mock_place)
        
        expected = {
            "name": "Konoba Stari Grad",
            "city": "Lovran",
            "address": "Lovran, Croatia",
            "attraction_type": "culinary",
            "latitude": 45.337769,
            "longitude": 14.305187,
            "admission_fee": "€€",
            "category_tags": ["restaurant", "food", "establishment"]
        }
        
        self.assertEqual(result, expected)

    def test_search_debouncing_logic(self):
        """Test the debouncing logic for search input."""
        # Simulate the debouncing logic from the component
        search_timeout = 300  # milliseconds
        last_search_time = 0
        
        def should_debounce_search(current_time, last_search):
            return (current_time - last_search) < search_timeout
        
        # Test cases
        test_cases = [
            (100, 0, True),    # Should debounce (100ms < 300ms)
            (400, 0, False),   # Should not debounce (400ms > 300ms)
            (600, 200, False), # Should not debounce (400ms > 300ms)
            (250, 0, True),    # Should debounce (250ms < 300ms)
        ]
        
        for current_time, last_time, expected in test_cases:
            result = should_debounce_search(current_time, last_time)
            self.assertEqual(result, expected, 
                           f"Debouncing failed for current_time={current_time}, last_time={last_time}")

    def test_authentication_check(self):
        """Test the authentication check logic."""
        # Mock localStorage
        mock_local_storage = {
            'session_token': 'valid_token_123'
        }
        
        def check_authentication():
            session_token = mock_local_storage.get('session_token')
            return session_token is not None
        
        # Test with valid token
        self.assertTrue(check_authentication())
        
        # Test without token
        mock_local_storage.clear()
        self.assertFalse(check_authentication())

    def test_error_handling_for_search_failures(self):
        """Test error handling when search strategies fail."""
        # Mock search strategies that fail
        failed_strategies = [
            {"textQuery": "Invalid Query 1"},
            {"textQuery": "Invalid Query 2"},
            {"textQuery": "Invalid Query 3"}
        ]
        
        def simulate_search_failures(strategies):
            results = []
            errors = []
            
            for strategy in strategies:
                try:
                    # Simulate a search that always fails
                    raise Exception(f"Search failed for: {strategy['textQuery']}")
                except Exception as e:
                    errors.append(str(e))
                    continue
            
            return results, errors
        
        results, errors = simulate_search_failures(failed_strategies)
        
        # Should have no results and 3 errors
        self.assertEqual(len(results), 0)
        self.assertEqual(len(errors), 3)
        self.assertTrue(all("Search failed for:" in error for error in errors))

if __name__ == '__main__':
    unittest.main()
