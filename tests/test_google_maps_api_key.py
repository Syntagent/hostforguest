"""
Simple test to verify Google Maps API key configuration.
"""

import os
import pytest


def test_google_maps_api_key_configured():
    """Test that Google Maps API key is properly configured."""
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Check that API key exists
    assert api_key is not None, "GOOGLE_MAPS_API_KEY environment variable is not set"
    
    # Check that API key is not empty
    assert api_key.strip() != "", "GOOGLE_MAPS_API_KEY is empty"
    
    # Check that API key has proper format (starts with AIza)
    assert api_key.startswith('AIza'), f"Google Maps API key should start with 'AIza', got: {api_key[:10]}..."
    
    # Check that API key has reasonable length
    assert len(api_key) > 30, f"Google Maps API key seems too short: {len(api_key)} characters"
    
    print(f"✅ Google Maps API key is properly configured: {api_key[:10]}...")


def test_google_ai_api_key_configured():
    """Test that Google AI API key is also configured."""
    api_key = os.getenv('GOOGLE_AI_API_KEY')
    
    # Check that API key exists
    assert api_key is not None, "GOOGLE_AI_API_KEY environment variable is not set"
    
    # Check that API key is not empty
    assert api_key.strip() != "", "GOOGLE_AI_API_KEY is empty"
    
    # Check that API key has proper format (starts with AIza)
    assert api_key.startswith('AIza'), f"Google AI API key should start with 'AIza', got: {api_key[:10]}..."
    
    print(f"✅ Google AI API key is properly configured: {api_key[:10]}...")


def test_environment_variables_loaded():
    """Test that environment variables are properly loaded from .env file."""
    # Test that we can access environment variables
    google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY')
    google_ai_key = os.getenv('GOOGLE_AI_API_KEY')
    
    assert google_maps_key is not None, "Environment variables not loaded from .env file"
    assert google_ai_key is not None, "Environment variables not loaded from .env file"
    
    print("✅ Environment variables are properly loaded from .env file")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
