"""Insights tab UI regression strings."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src"


def read_frontend(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_insights_shows_source_health_panel():
    src = read_frontend("components/dashboard/insights-tab.tsx")
    api = read_frontend("lib/api.ts")
    assert "Source health" in src
    assert "getSourcesHealth" in api


def test_insights_suggested_sources_approve_reject():
    src = read_frontend("components/dashboard/insights-tab.tsx")
    assert "Suggested sources" in src
    assert "approveProposal" in src or "Approve" in src


def test_insights_event_dates_display():
    src = read_frontend("components/dashboard/insights-tab.tsx")
    assert "start_at" in src
    assert "formatEventDates" in src
