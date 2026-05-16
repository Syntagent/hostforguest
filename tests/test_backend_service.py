"""HostService.update_host_profile smoke test on the async SQLite test DB."""

import uuid

import pytest

from app.models.host import HostCreate, HostProfileCreate, HostProfileUpdate
from app.services.host_service import HostService


@pytest.mark.asyncio
async def test_backend_service(db_session):
    email = f"backend-svc-{uuid.uuid4().hex[:12]}@example.com"
    svc = HostService(db_session)
    created = await svc.create_host(
        HostCreate(
            email=email,
            password="testpassword123",
            first_name="Back",
            last_name="End",
            address="1 Service St",
            city="Lovran",
            country="Croatia",
        )
    )
    assert created is not None
    host = await svc.get_host_by_id(created.id)
    assert host is not None

    prof = await svc.create_host_profile(
        host.id,
        HostProfileCreate(
            property_type="apartment",
            number_of_rooms=2,
            max_guests=4,
        ),
    )
    assert prof is not None

    update_data = HostProfileUpdate(
        property_name="Villa Adriatica",
        property_type="apartment",
        max_guests=6,
        number_of_rooms=3,
    )
    result = await svc.update_host_profile(host.id, update_data)
    assert result is not None
