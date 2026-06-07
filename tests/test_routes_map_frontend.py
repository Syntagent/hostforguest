"""Frontend guard for route map waypoint interactions."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db


ROOT = Path(__file__).resolve().parents[1]


def test_interactive_map_exposes_click_and_drag_hooks():
    source = (
        ROOT / "frontend" / "src" / "components" / "maps" / "InteractiveMap.tsx"
    ).read_text()

    assert "onMapClick?: (coords:" in source
    assert "draggableLocationIds?: string[]" in source
    assert "onMarkerDragEnd?: (location:" in source
    assert 'marker.addListener("dragend"' in source
    assert 'map.addListener("click"' in source


def test_routes_tab_uses_map_hooks_for_waypoints_and_reorder():
    source = (
        ROOT / "frontend" / "src" / "components" / "dashboard" / "routes-tab.tsx"
    ).read_text()

    assert "handleMapWaypointAdd" in source
    assert "itinerariesApi.createRoutePoint" in source
    assert "handleMapMarkerDragEnd" in source
    assert "itinerariesApi.reorderRoutePoints" in source
    assert "draggableLocationIds={routeMapLocations.map" in source
    assert "onMapClick={addWaypointFromMap ? handleMapWaypointAdd : undefined}" in source


def test_frontend_layout_does_not_fetch_google_fonts_at_build_time():
    source = (ROOT / "frontend" / "src" / "app" / "layout.tsx").read_text()

    assert "next/font/google" not in source
    assert "--font-body" in source
    assert "--font-display" in source
