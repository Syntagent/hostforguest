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
    map_source = (
        ROOT / "frontend" / "src" / "components" / "dashboard" / "route-day-map.tsx"
    ).read_text()

    assert "handleMapWaypointAdd" in source
    assert "itinerariesApi.createRoutePoint" in source
    assert "handleMapMarkerDragEnd" in source
    assert "itinerariesApi.reorderRoutePoints" in source
    assert 'import("./route-day-map")' in source
    assert "ssr: false" in source
    assert "draggableLocationIds={routeMapLocations.map" in source
    assert "onMapClick={addWaypointFromMap ? handleMapWaypointAdd : undefined}" in source
    assert "const orderedDayIds = sortedActivities.map((activity) => activity.id)" in source
    assert "ordered_activity_ids: fullDayIds" in source
    assert "GoogleMapsProvider" in map_source
    assert "InteractiveMap" in map_source


def test_frontend_layout_does_not_fetch_google_fonts_at_build_time():
    source = (ROOT / "frontend" / "src" / "app" / "layout.tsx").read_text()

    assert "next/font/google" not in source
    assert "--font-body" in source
    assert "--font-display" in source


def test_tailwind_source_scanning_is_limited_to_frontend_sources():
    source = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text()

    assert '@import "tailwindcss" source(none);' in source
    assert '@source "../app";' in source
    assert '@source "../components";' in source
    assert '@source "../contexts";' in source
    assert '@source "../lib";' in source


def test_next_pwa_is_not_loaded_unless_explicitly_enabled():
    source = (ROOT / "frontend" / "next.config.ts").read_text()
    compact_source = "".join(source.split())

    assert 'NEXT_PWA === "true"' in source
    assert 'from "@ducanh2912/next-pwa"' not in source
    assert 'require("@ducanh2912/next-pwa")' in compact_source
    assert "if (nextPwaExplicitlyEnabled)" in source


def test_next_build_does_not_force_single_worker_docker_builds():
    source = (ROOT / "frontend" / "next.config.ts").read_text()

    assert "cpus: 1" not in source
    assert "workerThreads: false" not in source
    assert "staticGenerationMaxConcurrency: 1" not in source
    assert "staticGenerationRetryCount: 0" in source
    assert "webpackBuildWorker: false" not in source


def test_next_config_loads_root_env_conditionally_and_quietly():
    source = (ROOT / "frontend" / "next.config.ts").read_text()

    assert "fs.existsSync(rootEnvPath)" in source
    assert "config({ path: rootEnvPath, quiet: true })" in source


def test_docker_build_can_disable_frontend_minification():
    config_source = (ROOT / "frontend" / "next.config.ts").read_text()
    docker_source = (ROOT / "frontend" / "Dockerfile").read_text()

    assert "DISABLE_FRONTEND_MINIFY=1" in docker_source
    assert 'process.env.DISABLE_FRONTEND_MINIFY === "1"' in config_source
    assert "config.optimization.minimize = false" in config_source


def test_frontend_build_does_not_transpile_framer_motion():
    source = (ROOT / "frontend" / "next.config.ts").read_text()

    assert "transpilePackages" not in source
    assert 'transpilePackages: ["framer-motion"' not in source


def test_dashboard_does_not_bundle_legacy_inline_accommodation_tab():
    source = (
        ROOT / "frontend" / "src" / "components" / "dashboard" / "host-dashboard.tsx"
    ).read_text()

    assert "Legacy inline tab retained temporarily" not in source
    assert "const AccommodationTab: React.FC" not in source
    assert "AccommodationAgentTab" in source


def test_dashboard_page_loads_heavy_client_dynamically():
    source = (ROOT / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text()

    assert 'import dynamic from "next/dynamic"' in source
    assert 'dynamic(() => import("./dashboard-client")' in source
    assert "ssr: false" in source


def test_docker_frontend_build_disables_next_telemetry():
    source = (ROOT / "frontend" / "Dockerfile").read_text()

    assert "ENV NEXT_TELEMETRY_DISABLED=1" in source


def test_docker_frontend_production_build_uses_single_stable_next_build():
    source = (ROOT / "frontend" / "Dockerfile").read_text()

    assert "RUN npm run build" in source
    assert "--turbopack" not in source
    assert "--experimental-build-mode" not in source


def test_docker_frontend_build_uses_cached_alpine_dependency_path():
    source = (ROOT / "frontend" / "Dockerfile").read_text()

    assert "FROM node:20-alpine AS deps" in source
    assert "RUN npm ci" in source
    assert "/app/frontend/.next/standalone" in source
    assert "/app/frontend/.next/static" in source
    assert "USER nextjs" in source
