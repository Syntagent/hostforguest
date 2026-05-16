"""
Test E-Visitor functionality for Croatian tourist registration compliance.

Skipped: legacy sync ``Session`` / ``db`` fixtures do not match async SQLAlchemy
test stack; rewrite with ``async_client`` + ``db_session`` (P0b backlog).
"""

import pytest

pytestmark = pytest.mark.skip(reason="Legacy sync DB fixtures; rewrite with async_client + db_session (P0b).")

import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.guest_group import GuestGroup, GuestEVisitorData
from app.services.guest_group_service import GuestGroupService
from app.core.config import settings
from app.services.host_service import HostService
from app.services.guest_group_service import GuestGroupService


class TestEVisitorFunctionality:
    """Test E-Visitor data management functionality."""

    def test_create_evisitor_data(self, client: TestClient, session: Session):
        """Test creating e-visitor data for a guest."""
        # Create test host and guest group
        host = create_test_host(session)
        guest_group = create_test_guest_group(session, host.id)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        assert login_response.status_code == 200
        session_token = login_response.json()["session_token"]
        
        # Create e-visitor data
        evisitor_data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "nationality": "Germany",
            "id_type": "passport",
            "id_number": "DE123456789",
            "id_issuing_country": "Germany",
            "id_expiry_date": "2030-01-15",
            "address_line1": "Musterstraße 123",
            "city": "Berlin",
            "postal_code": "10115",
            "country": "Germany",
            "arrival_date": "2025-06-01",
            "departure_date": "2025-06-08",
            "email": "john.doe@example.com",
            "phone": "+49123456789"
        }
        
        response = client.post(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
            json=evisitor_data,
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["nationality"] == "Germany"
        assert data["id_type"] == "passport"
        assert data["id_number"] == "DE123456789"
        assert data["evisitor_registered"] == False
        assert "id" in data
        assert "guest_group_id" in data

    def test_get_evisitor_data(self, client: TestClient, session: Session):
        """Test retrieving e-visitor data for a guest group."""
        # Create test host and guest group
        host = create_test_host(session)
        guest_group = create_test_guest_group(session, host.id)
        
        # Create e-visitor data directly in database
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Jane",
            last_name="Smith",
            date_of_birth=datetime(1985, 5, 20),
            nationality="United Kingdom",
            id_type="passport",
            id_number="GB987654321",
            id_issuing_country="United Kingdom",
            arrival_date=datetime(2025, 7, 1),
            departure_date=datetime(2025, 7, 15),
            email="jane.smith@example.com"
        )
        session.add(evisitor_data)
        session.commit()
        session.refresh(evisitor_data)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Get e-visitor data
        response = client.get(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["first_name"] == "Jane"
        assert data[0]["last_name"] == "Smith"
        assert data[0]["nationality"] == "United Kingdom"

    def test_update_evisitor_data(self, client: TestClient, session: Session):
        """Test updating e-visitor data."""
        # Create test host and guest group
        host = create_test_host(session)
        guest_group = create_test_guest_group(session, host.id)
        
        # Create e-visitor data directly in database
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Bob",
            last_name="Johnson",
            date_of_birth=datetime(1975, 12, 10),
            nationality="United States",
            id_type="passport",
            id_number="US123456789",
            id_issuing_country="United States",
            arrival_date=datetime(2025, 8, 1),
            departure_date=datetime(2025, 8, 10),
            email="bob.johnson@example.com"
        )
        db.add(evisitor_data)
        db.commit()
        db.refresh(evisitor_data)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Update e-visitor data
        update_data = {
            "phone": "+1234567890",
            "address_line1": "123 Main Street",
            "city": "New York",
            "state_province": "NY",
            "postal_code": "10001",
            "country": "United States"
        }
        
        response = client.put(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data/{evisitor_data.id}",
            json=update_data,
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+1234567890"
        assert data["address_line1"] == "123 Main Street"
        assert data["city"] == "New York"
        assert data["first_name"] == "Bob"  # Unchanged fields should remain

    def test_mark_evisitor_registered(self, client: TestClient, session: Session):
        """Test marking e-visitor data as registered."""
        # Create test host and guest group
        host = create_test_host(db)
        guest_group = create_test_guest_group(db, host.id)
        
        # Create e-visitor data directly in database
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Alice",
            last_name="Brown",
            date_of_birth=datetime(1992, 3, 25),
            nationality="Canada",
            id_type="passport",
            id_number="CA987654321",
            id_issuing_country="Canada",
            arrival_date=datetime(2025, 9, 1),
            departure_date=datetime(2025, 9, 14),
            email="alice.brown@example.com"
        )
        db.add(evisitor_data)
        db.commit()
        db.refresh(evisitor_data)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Mark as registered
        registration_data = {
            "confirmation_number": "EVI-2025-001234"
        }
        
        response = client.post(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data/{evisitor_data.id}/register",
            json=registration_data,
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["evisitor_registered"] == True
        assert data["evisitor_confirmation_number"] == "EVI-2025-001234"
        assert data["evisitor_registration_date"] is not None

    def test_delete_evisitor_data(self, client: TestClient, session: Session):
        """Test deleting e-visitor data."""
        # Create test host and guest group
        host = create_test_host(db)
        guest_group = create_test_guest_group(db, host.id)
        
        # Create e-visitor data directly in database
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Charlie",
            last_name="Wilson",
            date_of_birth=datetime(1988, 7, 15),
            nationality="Australia",
            id_type="passport",
            id_number="AU123456789",
            id_issuing_country="Australia",
            arrival_date=datetime(2025, 10, 1),
            departure_date=datetime(2025, 10, 10),
            email="charlie.wilson@example.com"
        )
        db.add(evisitor_data)
        db.commit()
        db.refresh(evisitor_data)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Delete e-visitor data
        response = client.delete(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data/{evisitor_data.id}",
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
            headers={"X-Session-Token": session_token}
        )
        assert get_response.status_code == 200
        assert len(get_response.json()) == 0

    def test_evisitor_data_validation(self, client: TestClient, session: Session):
        """Test e-visitor data validation."""
        # Create test host and guest group
        host = create_test_host(db)
        guest_group = create_test_guest_group(db, host.id)
        
        # Login as host
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Test missing required fields
        invalid_data = {
            "first_name": "John",
            "last_name": "Doe"
            # Missing required fields
        }
        
        response = client.post(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
            json=invalid_data,
            headers={"X-Session-Token": session_token}
        )
        
        assert response.status_code == 422  # Validation error

    def test_evisitor_data_unauthorized_access(self, client: TestClient, session: Session):
        """Test unauthorized access to e-visitor data."""
        # Create test host and guest group
        host = create_test_host(db)
        guest_group = create_test_guest_group(db, host.id)
        
        # Create e-visitor data directly in database
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Test",
            last_name="User",
            date_of_birth=datetime(1990, 1, 1),
            nationality="Test",
            id_type="passport",
            id_number="TEST123",
            id_issuing_country="Test",
            arrival_date=datetime(2025, 1, 1),
            departure_date=datetime(2025, 1, 10)
        )
        db.add(evisitor_data)
        db.commit()
        db.refresh(evisitor_data)
        
        # Try to access without authentication
        response = client.get(f"/api/v1/guest-groups/{guest_group.id}/evisitor-data")
        assert response.status_code == 401  # Unauthorized

    def test_evisitor_data_wrong_host(self, client: TestClient, session: Session):
        """Test access to e-visitor data by wrong host."""
        # Create two hosts
        host1 = create_test_host(db, email="host1@example.com")
        host2 = create_test_host(db, email="host2@example.com")
        
        # Create guest group for host1
        guest_group = create_test_guest_group(db, host1.id)
        
        # Create e-visitor data for host1's group
        evisitor_data = GuestEVisitorData(
            guest_group_id=guest_group.id,
            first_name="Test",
            last_name="User",
            date_of_birth=datetime(1990, 1, 1),
            nationality="Test",
            id_type="passport",
            id_number="TEST123",
            id_issuing_country="Test",
            arrival_date=datetime(2025, 1, 1),
            departure_date=datetime(2025, 1, 10)
        )
        db.add(evisitor_data)
        db.commit()
        db.refresh(evisitor_data)
        
        # Login as host2
        login_response = client.post("/api/v1/hosts/login", json={
            "email": "host2@example.com",
            "password": "testpassword123"
        })
        session_token = login_response.json()["session_token"]
        
        # Try to access host1's e-visitor data
        response = client.get(
            f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 404  # Not found (wrong host)


def test_evisitor_data_complete_workflow(client: TestClient, session: Session):
    """Test complete e-visitor data workflow."""
    # Create test host and guest group
    host = create_test_host(db)
    guest_group = create_test_guest_group(db, host.id)
    
    # Login as host
    login_response = client.post("/api/v1/hosts/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    session_token = login_response.json()["session_token"]
    
    # 1. Create e-visitor data
    evisitor_data = {
        "first_name": "Maria",
        "last_name": "Garcia",
        "date_of_birth": "1985-08-20",
        "nationality": "Spain",
        "id_type": "id_card",
        "id_number": "ES12345678A",
        "id_issuing_country": "Spain",
        "arrival_date": "2025-06-15",
        "departure_date": "2025-06-22",
        "email": "maria.garcia@example.com",
        "phone": "+34612345678"
    }
    
    create_response = client.post(
        f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
        json=evisitor_data,
        headers={"X-Session-Token": session_token}
    )
    assert create_response.status_code == 201
    created_data = create_response.json()
    evisitor_id = created_data["id"]
    
    # 2. Verify data was created
    get_response = client.get(
        f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
        headers={"X-Session-Token": session_token}
    )
    assert get_response.status_code == 200
    assert len(get_response.json()) == 1
    
    # 3. Update the data
    update_data = {
        "phone": "+34687654321",
        "address_line1": "Calle Mayor 123",
        "city": "Madrid",
        "postal_code": "28001",
        "country": "Spain"
    }
    
    update_response = client.put(
        f"/api/v1/guest-groups/{guest_group.id}/evisitor-data/{evisitor_id}",
        json=update_data,
        headers={"X-Session-Token": session_token}
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["phone"] == "+34687654321"
    
    # 4. Mark as registered
    register_response = client.post(
        f"/api/v1/guest-groups/{guest_group.id}/evisitor-data/{evisitor_id}/register",
        json={"confirmation_number": "EVI-2025-005678"},
        headers={"X-Session-Token": session_token}
    )
    assert register_response.status_code == 200
    registered_data = register_response.json()
    assert registered_data["evisitor_registered"] == True
    assert registered_data["evisitor_confirmation_number"] == "EVI-2025-005678"
    
    # 5. Verify final state
    final_response = client.get(
        f"/api/v1/guest-groups/{guest_group.id}/evisitor-data",
        headers={"X-Session-Token": session_token}
    )
    assert final_response.status_code == 200
    final_data = final_response.json()[0]
    assert final_data["evisitor_registered"] == True
    assert final_data["evisitor_confirmation_number"] == "EVI-2025-005678"
    assert final_data["phone"] == "+34687654321"
