"""
Tests for main application endpoints.

Tests the root endpoint, health check, and basic application functionality.
"""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_read_root(client: TestClient):
    """
    Test the root endpoint.
    
    Args:
        client: FastAPI test client
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Welcome to {settings.app_name}"
    assert data["version"] == "1.0.0"
    assert data["status"] == "healthy"
    assert data["environment"] == "development"


def test_health_check(client: TestClient):
    """
    Test the health check endpoint.
    
    Args:
        client: FastAPI test client
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == settings.app_name
    assert data["version"] == "1.0.0"


def test_health_check_response_structure(client: TestClient):
    """
    Test health check response structure and content.
    
    Args:
        client: FastAPI test client
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    required_fields = ["status", "app", "version"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Verify field types
    assert isinstance(data["status"], str)
    assert isinstance(data["app"], str)
    assert isinstance(data["version"], str) 