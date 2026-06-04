"""Legacy Live voice config removed — ingest endpoint is the voice surface."""

from app.api.v1.accommodation_voice import router


def test_voice_router_exposes_ingest_not_live_stream():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/ingest" in paths or "ingest" in str(paths)
    assert not any("stream" in str(p) for p in paths)
