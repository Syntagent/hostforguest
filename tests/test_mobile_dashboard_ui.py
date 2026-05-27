"""Regression checks for mobile dashboard polish."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")


def test_mobile_shell_uses_primary_nav_and_more_sheet():
    source = read_frontend("components/layout/app-layout.tsx")

    assert "primaryMobileItems = navItems.slice(0, 4)" in source
    assert "overflowMobileItems = navItems.slice(4)" in source
    assert "More sections" in source
    assert "fixed inset-x-0 bottom-0" in source
    assert "pb-[calc(5.25rem+env(safe-area-inset-bottom))]" in source


def test_accommodation_tab_has_compact_mobile_photo_gallery():
    source = read_frontend("components/dashboard/host-dashboard.tsx")
    accommodation_tab = read_frontend("components/dashboard/accommodation-tab.tsx")
    checklist_defs = read_frontend("components/dashboard/accommodation-ai-agent/accommodation-checklist.ts")
    checklist = read_frontend("components/dashboard/accommodation-ai-agent/agent-checklist.tsx")

    assert "Property profile" in source
    assert "Your accommodation" in source
    assert "More property details" in source
    assert 'className={cn("grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-3 lg:gap-6", !isEditing && "hidden sm:grid")}' in source
    assert "overflow-x-auto" in source
    assert '<Card className="hidden sm:block">' in source
    assert "hidden bg-gradient-to-br from-yellow-50 to-orange-50 sm:block" in source
    assert "Edit fields manually" in accommodation_tab
    assert "h-8 w-8 min-h-0" in accommodation_tab
    assert "focusMissingField" in accommodation_tab
    assert 'id="stay-capacity"' in accommodation_tab
    assert 'id="stay-amenities"' in accommodation_tab
    assert "CHECKLIST_EDIT_TARGETS" in checklist_defs
    assert "Fix {item.label ?? item.id}" in checklist
    assert "onEditMissing?.(item.id)" in checklist
    assert "hidden space-y-1.5 sm:block" in checklist
    assert "alert(" not in source

