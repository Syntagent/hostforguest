from pathlib import Path


def test_horizontal_chip_scroller_enables_mobile_swipe_layout():
    source = Path("frontend/src/components/dashboard/accommodation-ai-agent/horizontal-chip-scroller.tsx").read_text()
    assert "overflow-x-auto" in source
    assert "touch-pan-x" in source
    assert "w-max" in source
    assert "min-w-0" in source

    panel_source = Path(
        "frontend/src/components/dashboard/accommodation-ai-agent/accommodation-ai-agent-panel.tsx"
    ).read_text()
    assert "HorizontalChipScroller" in panel_source
