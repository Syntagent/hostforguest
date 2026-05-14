"""
Test for the Google Gemini Pydantic structured output fix.

Verifies that the AI Profile Generation now works consistently with the 
enhanced fallback handling for Gemini's structured output issues.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.host_onboarding_service import HostOnboardingService, AIProfileSuggestions
from app.services.ai_service_fallback import AIServiceWithFallback

logger = logging.getLogger(__name__)


class TestGeminiStructuredOutputFix:
    """Test suite for the Gemini structured output fix."""
    
    @pytest.fixture
    def host_onboarding_service(self, db_session: AsyncSession):
        """Create host onboarding service instance."""
        return HostOnboardingService(db_session)
    
    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service."""
        mock_service = AsyncMock(spec=AIServiceWithFallback)
        return mock_service
    
    @pytest.fixture
    def sample_host_info(self):
        """Sample host information for testing."""
        return {
            "first_name": "Marija",
            "last_name": "Petrović",
            "business_name": "Villa Adriatic",
            "city": "Lovran",
            "address": "Oprić 71, Lovran 51450",
            "region": "Primorsko-goranska",
            "business_type": "villa",
            "max_group_size": 8,
            "languages": ["hr", "en", "de"],
            "specialties": ["istrian_cuisine", "wine_tours", "hiking"],
            "local_experience": "born_here",
            "location_story": "I was born in Lovran and have been sharing its beauty with guests for over 10 years. My family has roots here dating back generations.",
            "preferred_guests": ["families", "couples", "food_lovers"]
        }
    
    async def test_native_gemini_structured_output_success(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test successful native Gemini structured output."""
        # Arrange
        expected_suggestions = {
            "business_description": [
                "Welcome to Villa Adriatic in Lovran! I'm Marija and I'm excited to share my born_here experience with you.",
                "As someone who has been born and raised here, I know Lovran like the back of my hand. My specialties include istrian_cuisine, wine_tours, hiking."
            ],
            "welcome_message": [
                "Dobrodošli! I'm Marija Petrović and I can't wait to welcome you to Lovran!",
                "Welcome to Villa Adriatic! With my local knowledge, I'll help you discover wine_tours, hiking experiences."
            ],
            "local_specialties": ["istrian_cuisine", "wine_tours", "hiking"],
            "host_story": [
                "I'm Marija Petrović from Lovran. I was born in Lovran and have been sharing its beauty with guests for over 10 years.",
                "My experience: born_here. I love sharing istrian_cuisine, wine_tours with my guests."
            ],
            "experience_promise": [
                "With my born_here experience and expertise in istrian_cuisine, wine_tours, hiking, you'll discover the authentic Lovran.",
                "I personally ensure every guest experiences the real Lovran through wine_tours, hiking recommendations."
            ]
        }
        
        mock_ai_service.generate_structured_response.return_value = {
            "success": True,
            "structured_data": expected_suggestions,
            "provider": "google_gemini_native",
            "model": "gemini-2.5-flash"
        }
        
        # Replace the AI service
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        
        # Assert
        assert result["success"] is True
        assert "suggestions" in result
        assert result["provider"] == "google_gemini_native"
        
        # Verify all required fields are present
        suggestions = result["suggestions"]
        assert "business_description" in suggestions
        assert "welcome_message" in suggestions
        assert "local_specialties" in suggestions
        assert "host_story" in suggestions
        assert "experience_promise" in suggestions
        
        # Verify field types
        assert isinstance(suggestions["business_description"], list)
        assert isinstance(suggestions["welcome_message"], list)
        assert isinstance(suggestions["local_specialties"], list)
        assert isinstance(suggestions["host_story"], list)
        assert isinstance(suggestions["experience_promise"], list)
        
        # Verify content includes personal information
        business_desc = ' '.join(suggestions["business_description"])
        assert "Marija" in business_desc
        assert "Lovran" in business_desc
    
    async def test_enhanced_json_guided_generation_fallback(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test enhanced JSON-guided generation fallback."""
        # Arrange - simulate native structured output failure, enhanced success
        expected_suggestions = {
            "business_description": [
                "Welcome to Villa Adriatic in beautiful Lovran! I'm Marija, your local host.",
                "Born and raised in Lovran, I specialize in istrian_cuisine and wine_tours."
            ],
            "welcome_message": [
                "Dobrodošli to Villa Adriatic! I'm Marija and I'm thrilled to share Lovran with you.",
                "Welcome! With my local expertise, I'll show you the best of istrian_cuisine and hiking."
            ],
            "local_specialties": ["istrian_cuisine", "wine_tours", "hiking"],
            "host_story": [
                "I'm Marija Petrović, born in Lovran with deep family roots here.",
                "My story: I was born in Lovran and have been sharing its beauty with guests for over 10 years."
            ],
            "experience_promise": [
                "With my born_here knowledge, you'll experience authentic Lovran.",
                "I promise personalized recommendations for istrian_cuisine and wine_tours."
            ]
        }
        
        mock_ai_service.generate_structured_response.return_value = {
            "success": True,
            "structured_data": expected_suggestions,
            "provider": "google_gemini_enhanced",
            "model": "gemini-2.5-flash"
        }
        
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        
        # Assert
        assert result["success"] is True
        assert result["provider"] == "google_gemini_enhanced"
        
        suggestions = result["suggestions"]
        assert len(suggestions["business_description"]) >= 1
        assert len(suggestions["welcome_message"]) >= 1
        assert len(suggestions["local_specialties"]) >= 1
        assert len(suggestions["host_story"]) >= 1
        assert len(suggestions["experience_promise"]) >= 1
    
    async def test_fallback_parsing_when_structured_fails(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test fallback to manual parsing when structured output fails."""
        # Arrange - simulate structured output failure, fallback success
        mock_ai_service.generate_structured_response.return_value = {
            "success": False,
            "error": "All structured output attempts failed"
        }
        
        # Mock successful fallback chat response
        mock_ai_service.generate_chat_response.return_value = {
            "success": True,
            "response": """Here are my suggestions for Villa Adriatic:

Business Description:
- Welcome to Villa Adriatic in Lovran! I'm Marija, your local host with deep family roots.
- Born and raised here, I specialize in istrian_cuisine, wine_tours, and hiking experiences.

Welcome Messages:
- Dobrodošli to Villa Adriatic! I'm Marija and I'm excited to share Lovran's beauty with you.
- Welcome! With my local knowledge, I'll help you discover the authentic side of Lovran.

Local Specialties:
- istrian_cuisine
- wine_tours  
- hiking

Host Story:
- I'm Marija Petrović from Lovran. I was born in Lovran and have been sharing its beauty with guests for over 10 years.
- My family has deep roots here and I love sharing our local traditions with visitors.

Experience Promise:
- With my born_here knowledge and expertise in istrian_cuisine, you'll discover the real Lovran.
- I personally ensure every guest experiences authentic local culture and hidden gems.""",
            "model": "gemini-2.5-flash"
        }
        
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        
        # Assert
        assert result["success"] is True
        assert result["provider"] == "fallback_parsing"
        
        suggestions = result["suggestions"]
        assert "business_description" in suggestions
        assert "welcome_message" in suggestions
        assert "local_specialties" in suggestions
        assert "host_story" in suggestions
        assert "experience_promise" in suggestions
        
        # Verify personal information is preserved
        business_desc = ' '.join(suggestions["business_description"])
        assert "Marija" in business_desc
        assert "Villa Adriatic" in business_desc
        assert "Lovran" in business_desc
    
    async def test_complete_failure_handling(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test handling when all AI generation methods fail."""
        # Arrange - simulate all methods failing
        mock_ai_service.generate_structured_response.return_value = {
            "success": False,
            "error": "Structured output failed"
        }
        
        mock_ai_service.generate_chat_response.return_value = {
            "success": False,
            "error": "Chat response failed"
        }
        
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "All AI generation methods failed" in result["error"]
    
    def test_pydantic_model_validation(self):
        """Test that the AIProfileSuggestions Pydantic model validates correctly."""
        # Arrange
        valid_data = {
            "business_description": ["Description 1", "Description 2"],
            "welcome_message": ["Welcome 1", "Welcome 2"],
            "local_specialties": ["Specialty 1", "Specialty 2"],
            "host_story": ["Story 1", "Story 2"],
            "experience_promise": ["Promise 1", "Promise 2"]
        }
        
        # Act & Assert - should not raise
        suggestions = AIProfileSuggestions(**valid_data)
        assert suggestions.business_description == valid_data["business_description"]
        assert suggestions.welcome_message == valid_data["welcome_message"]
        assert suggestions.local_specialties == valid_data["local_specialties"]
        assert suggestions.host_story == valid_data["host_story"]
        assert suggestions.experience_promise == valid_data["experience_promise"]
    
    def test_pydantic_model_validation_missing_fields(self):
        """Test that the AIProfileSuggestions model fails validation with missing fields."""
        # Arrange - missing required fields
        incomplete_data = {
            "business_description": ["Description 1"],
            "welcome_message": ["Welcome 1"]
            # Missing: local_specialties, host_story, experience_promise
        }
        
        # Act & Assert - should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            AIProfileSuggestions(**incomplete_data)
    
    async def test_personal_information_preservation(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test that personal information from host is preserved in suggestions."""
        # Arrange
        expected_suggestions = {
            "business_description": [
                "Welcome to Villa Adriatic in Lovran! I'm Marija and I'm excited to share my born_here experience with you.",
                "As someone who has been born and raised here, I know Lovran like the back of my hand. My specialties include istrian_cuisine, wine_tours, hiking."
            ],
            "welcome_message": [
                "Dobrodošli! I'm Marija Petrović and I can't wait to welcome you to Lovran!",
                "Welcome to Villa Adriatic! With my local knowledge, I'll help you discover wine_tours, hiking experiences."
            ],
            "local_specialties": ["istrian_cuisine", "wine_tours", "hiking"],
            "host_story": [
                "I'm Marija Petrović from Lovran. I was born in Lovran and have been sharing its beauty with guests for over 10 years.",
                "My experience: born_here. I love sharing istrian_cuisine, wine_tours with my guests."
            ],
            "experience_promise": [
                "With my born_here experience and expertise in istrian_cuisine, wine_tours, hiking, you'll discover the authentic Lovran.",
                "I personally ensure every guest experiences the real Lovran through wine_tours, hiking recommendations."
            ]
        }
        
        mock_ai_service.generate_structured_response.return_value = {
            "success": True,
            "structured_data": expected_suggestions,
            "provider": "google_gemini_native",
            "model": "gemini-2.5-flash"
        }
        
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        
        # Assert
        assert result["success"] is True
        suggestions = result["suggestions"]
        
        # Check that personal information is included
        all_text = ' '.join([
            ' '.join(suggestions["business_description"]),
            ' '.join(suggestions["welcome_message"]),
            ' '.join(suggestions["host_story"]),
            ' '.join(suggestions["experience_promise"])
        ])
        
        # Verify personal details are preserved
        assert "Marija" in all_text
        assert "Petrović" in all_text
        assert "Villa Adriatic" in all_text
        assert "Lovran" in all_text
        assert "istrian_cuisine" in all_text
        assert "wine_tours" in all_text
        assert "hiking" in all_text
        assert "born_here" in all_text or "born and raised" in all_text.lower()
    
    async def test_response_time_performance(self, host_onboarding_service, mock_ai_service, sample_host_info):
        """Test that the response time meets the requirement of under 10 seconds."""
        import time
        
        # Arrange
        mock_ai_service.generate_structured_response.return_value = {
            "success": True,
            "structured_data": {
                "business_description": ["Test description"],
                "welcome_message": ["Test welcome"],
                "local_specialties": ["Test specialty"],
                "host_story": ["Test story"],
                "experience_promise": ["Test promise"]
            },
            "provider": "google_gemini_native",
            "model": "gemini-2.5-flash"
        }
        
        host_onboarding_service.ai_service = mock_ai_service
        
        # Act
        start_time = time.time()
        result = await host_onboarding_service.generate_host_profile_suggestions(sample_host_info)
        end_time = time.time()
        
        # Assert
        assert result["success"] is True
        response_time = end_time - start_time
        assert response_time < 10.0, f"Response time {response_time:.2f}s exceeds 10 second requirement"
