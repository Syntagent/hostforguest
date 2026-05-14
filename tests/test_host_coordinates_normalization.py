"""Host profile GPS: treat (0,0) placeholder as unset."""

from app.services.host_service import _coerce_placeholder_gps_to_none


def test_coerce_zero_zero_to_none():
    assert _coerce_placeholder_gps_to_none(0, 0) == (None, None)
    assert _coerce_placeholder_gps_to_none(0.0, 0.0) == (None, None)


def test_coerce_preserves_real_coordinates():
    assert _coerce_placeholder_gps_to_none(45.291, 14.274) == (45.291, 14.274)


def test_coerce_preserves_partial_null():
    assert _coerce_placeholder_gps_to_none(45.0, None) == (45.0, None)
    assert _coerce_placeholder_gps_to_none(None, 14.0) == (None, 14.0)
