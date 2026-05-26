"""Contract checks for CI Playwright guest-events harness."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
FRONTEND_PUBLIC = REPO_ROOT / "frontend" / "public"
RUN_SCRIPT = REPO_ROOT / "scripts" / "run-e2e-ci.sh"
SEED_SCRIPT = REPO_ROOT / "scripts" / "seed_e2e_guest.py"
PW_CONFIG = REPO_ROOT / "tests" / "e2e" / "playwright.ci.config.ts"
PW_GUEST_SPEC = REPO_ROOT / "tests" / "e2e" / "ci-guest-events.spec.ts"
PW_HOST_SPEC = REPO_ROOT / "tests" / "e2e" / "ci-host-dashboard.spec.ts"
PW_HOST_AUTH = REPO_ROOT / "tests" / "e2e" / "ci-host-auth.ts"


def test_e2e_ci_harness_files_exist() -> None:
    assert RUN_SCRIPT.is_file()
    assert os.access(RUN_SCRIPT, os.X_OK)
    assert SEED_SCRIPT.is_file()
    assert PW_CONFIG.is_file()
    assert PW_GUEST_SPEC.is_file()
    assert PW_HOST_SPEC.is_file()
    assert PW_HOST_AUTH.is_file()


def test_seed_e2e_guest_script_compiles() -> None:
    proc = subprocess.run(
        ["python3", "-m", "py_compile", str(SEED_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0


def test_run_e2e_ci_script_documents_stack_ports() -> None:
    text = RUN_SCRIPT.read_text(encoding="utf-8")
    assert "uvicorn app.main:app" in text
    assert "playwright.ci.config.ts" in text
    assert "seed_e2e_guest.py" in text
    assert "DEV_LOGIN_SEED_FORCE" in text
    assert "3055" in text
    assert "8000" in text


def test_playwright_ci_config_includes_host_dashboard() -> None:
    text = PW_CONFIG.read_text(encoding="utf-8")
    assert "ci-guest-events.spec.ts" in text
    assert "ci-host-dashboard.spec.ts" in text


def test_ci_host_dashboard_spec_covers_create_group_flow() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "Create New Group" in text
    assert "Create New Guest Group" in text
    assert "Create Group" in text


def test_ci_host_dashboard_spec_covers_channels_and_maintenance_tabs() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "channels and maintenance tabs load" in text
    assert 'openHostTab(page, "Channels")' in text
    assert 'openHostTab(page, "Maintenance")' in text
    assert "Booking.com" in text
    assert "Create issue" in text


def test_ci_host_dashboard_spec_covers_stay_routes_insights_tabs() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "stay, routes, and insights tabs load" in text
    assert 'openHostTab(page, "Stay")' in text
    assert 'openHostTab(page, "Routes")' in text
    assert 'openHostTab(page, "Insights")' in text
    assert "Accommodation Management" in text
    assert "Routes & itineraries" in text


def test_ci_host_dashboard_spec_covers_attractions_create_modal() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "attractions tab opens create modal" in text
    assert 'openHostTab(page, "Attractions")' in text
    assert "Add New Attraction" in text
    assert "Create New Attraction" in text


def test_ci_host_dashboard_spec_covers_attractions_create_submit() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "attractions tab creates attraction from address and city" in text
    assert "Create Attraction" in text
    assert "CI E2E Attraction" in text


def test_ci_host_dashboard_spec_covers_remaining_host_tabs() -> None:
    text = PW_HOST_SPEC.read_text(encoding="utf-8")
    assert "adaptation, map, discover, and cleaning tabs load" in text
    assert 'openHostTab(page, "Adaptation")' in text
    assert 'openHostTab(page, "Map")' in text
    assert 'openHostTab(page, "Discover")' in text
    assert 'openHostTab(page, "Cleaning")' in text


def test_github_ci_workflow_defines_e2e_smoke_job() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "e2e-smoke:" in text
    assert "e2e-guest-events:" not in text
    assert "bash scripts/run-e2e-ci.sh" in text


def test_frontend_public_has_no_committed_next_pwa_artifacts() -> None:
    """next-pwa writes sw/workbox files at build time when NEXT_PWA=true — not source."""
    assert not (FRONTEND_PUBLIC / "sw.js").exists()
    assert not list(FRONTEND_PUBLIC.glob("swe-worker-*.js"))
    assert not list(FRONTEND_PUBLIC.glob("workbox-*.js"))
