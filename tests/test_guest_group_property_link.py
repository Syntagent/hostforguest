"""Guest groups are linked to host accommodation (host_profiles) on create and in API responses."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_group import GuestGroupCreate
from app.models.host import Host, HostProfile
from app.services.guest_group_service import GuestGroupService


@pytest_asyncio.fixture
async def host_with_property_profile(async_db_session: AsyncSession) -> tuple[Host, HostProfile]:
    from app.services.host_service import HostService
    from app.models.host import HostCreate

    svc = HostService(async_db_session)
    created = await svc.create_host(
        HostCreate(
            email=f"prop-link-{uuid.uuid4().hex[:8]}@example.com",
            password="testpassword123",
            first_name="Host",
            last_name="Property",
            business_name="Biz",
            address="HQ",
            city="Rijeka",
            country="Croatia",
        )
    )
    assert created is not None
    host = await svc.get_host_by_id(created.id)
    assert host is not None

    profile = HostProfile(
        host_id=host.id,
        property_name="Sunrise Heights Lovran",
        property_type="apartment",
        city="Lovran",
        county="Primorje-Gorski Kotar County",
        address="71, 51415, Oprić, Croatia",
        latitude=45.311,
        longitude=14.2705,
    )
    async_db_session.add(profile)
    await async_db_session.commit()
    await async_db_session.refresh(profile)
    return host, profile


@pytest.mark.asyncio
async def test_create_guest_group_sets_host_profile_id(
    async_db_session: AsyncSession,
    host_with_property_profile: tuple[Host, HostProfile],
):
    host, profile = host_with_property_profile
    gsvc = GuestGroupService(async_db_session)
    res = await gsvc.create_guest_group(
        host.id,
        GuestGroupCreate(group_name="Spring guests", group_size=2),
    )
    assert res is not None
    assert res.host_profile_id == profile.id
    assert res.accommodation is not None
    assert res.accommodation.host_profile_id == profile.id
    assert res.accommodation.property_name == "Sunrise Heights Lovran"
    assert res.accommodation.city == "Lovran"

    row = await gsvc.get_guest_group_by_id(res.id)
    assert row is not None
    assert row.host_profile_id == profile.id


@pytest.mark.asyncio
async def test_list_host_groups_includes_same_accommodation(
    async_db_session: AsyncSession,
    host_with_property_profile: tuple[Host, HostProfile],
):
    host, profile = host_with_property_profile
    gsvc = GuestGroupService(async_db_session)
    await gsvc.create_guest_group(host.id, GuestGroupCreate(group_name="A", group_size=2))
    await gsvc.create_guest_group(host.id, GuestGroupCreate(group_name="B", group_size=3))

    listed = await gsvc.get_host_guest_groups(host.id, include_completed=True)
    assert len(listed) >= 2
    for g in listed:
        assert g.accommodation is not None
        assert g.accommodation.host_profile_id == profile.id
        assert g.accommodation.property_name == "Sunrise Heights Lovran"
