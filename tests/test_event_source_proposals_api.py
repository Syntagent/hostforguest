"""Event source proposal API routes exist."""

from pathlib import Path


def test_realtime_routes_include_proposals():
    src = (Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "realtime_data.py").read_text()
    assert "/sources/proposals" in src
    assert "approve_source_proposal" in src
    assert "discover_event_sources" in src
