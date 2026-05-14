"""UUID / status helpers for guest groups — avoids false 403/404/500 across drivers."""

import uuid

import pytest

from app.models.guest_group import AccessCodeStatus, GuestGroup
from app.services.guest_group_service import (
    _access_code_status_equals,
    host_owns_guest_group,
)


def test_host_owns_guest_group_uuid_vs_string():
    hid = uuid.uuid4()
    g = GuestGroup(
        id=uuid.uuid4(),
        host_id=hid,
        group_size=2,
    )
    assert host_owns_guest_group(g, hid)
    assert host_owns_guest_group(g, str(hid))
    assert not host_owns_guest_group(g, uuid.uuid4())


def test_host_owns_guest_group_none():
    assert not host_owns_guest_group(None, uuid.uuid4())


@pytest.mark.parametrize(
    "raw,expect_active",
    [
        (AccessCodeStatus.ACTIVE, True),
        ("active", True),
        ("ACTIVE", True),
        ("used", False),
        (AccessCodeStatus.USED, False),
    ],
)
def test_access_code_status_equals(raw, expect_active):
    assert _access_code_status_equals(raw, AccessCodeStatus.ACTIVE) is expect_active
