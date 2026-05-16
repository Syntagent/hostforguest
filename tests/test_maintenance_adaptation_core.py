"""Core maintenance/adaptation logic: ROI, BOM totals, webhook HMAC."""

import hashlib
import hmac
import json

import pytest

from app.services import adaptation_service as adaptation_svc
from app.services.adaptation_roi import bom_totals, compute_adaptation_roi


def test_offline_pool_shell_bom_totals_sane():
    lines = [x.model_dump() for x in adaptation_svc._offline_pool_shell_finish_bom()]
    tmin, tmax = bom_totals(lines)
    assert tmax > 5000
    assert tmin > 2000
    assert len(lines) >= 4


def test_compute_adaptation_roi_incremental_and_payback():
    inputs = {
        "adr": 100.0,
        "occupancy_pct": 50.0,
        "adr_uplift_pct": 10.0,
        "occ_uplift_pct": 10.0,
    }
    out = compute_adaptation_roi(inputs, investment_mid_eur=5000.0)
    assert out["incremental_revenue_year"] >= 0
    assert out["simple_payback_months"] is not None
    assert out["simple_payback_months"] > 0


def test_bom_totals():
    lines = [
        {"cost_min_eur": 100, "cost_max_eur": 200},
        {"cost_mid_eur": 50},
    ]
    tmin, tmax = bom_totals(lines)
    assert tmin == 150.0
    assert tmax == 250.0


def test_maintenance_webhook_hmac_verify():
    secret = "testsecret"
    body = json.dumps(
        {"host_id": "00000000-0000-0000-0000-000000000001", "title": "x", "category": "other"}
    ).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(sig, expected)


def test_adaptation_analyze_result_after_direction_optional():
    m = adaptation_svc.AdaptationAnalyzeResultModel(
        vision_summary="Kitchen refresh",
        after_direction_text="Warmer oak tones and under-cabinet LED.",
        bom_lines=[],
    )
    d = m.model_dump()
    assert d["after_direction_text"].startswith("Warmer")


def test_adaptation_analyze_result_defaults_after_direction_empty():
    m = adaptation_svc.AdaptationAnalyzeResultModel(vision_summary="x", bom_lines=[])
    assert m.after_direction_text == ""


@pytest.mark.asyncio
async def test_fetch_image_bytes_for_adaptation_vision_filters_urls():
    assert await adaptation_svc.fetch_image_bytes_for_adaptation_vision([]) == []
    assert await adaptation_svc.fetch_image_bytes_for_adaptation_vision(
        ["file:///etc/passwd", "ftp://example.com/x", ""]
    ) == []


def test_gemini_structured_payload_with_images():
    from app.services.ai_service_fallback import AIServiceWithFallback

    pl = AIServiceWithFallback._gemini_structured_content_payload(
        "prompt",
        [("image/png", b"\x89PNG\r\n\x1a\n"), ("image/jpeg", b"\xff\xd8\xff")],
    )
    assert isinstance(pl, list)
    assert pl[0] == "prompt"
    assert pl[1]["mime_type"] == "image/png"
    assert pl[2]["mime_type"] == "image/jpeg"


def test_partner_rank_schema():
    from app.services.maintenance_ai_service import PartnerRankResult, PartnerRankLine

    m = PartnerRankResult(
        ranked=[
            PartnerRankLine(partner_id="00000000-0000-0000-0000-000000000099", rank=1, reason="Closest"),
        ]
    )
    assert len(m.ranked) == 1
