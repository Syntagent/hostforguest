from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_PANEL = PROJECT_ROOT / "frontend/src/components/dashboard/accommodation-ai-agent/accommodation-ai-agent-panel.tsx"
AGENT_HOOK = PROJECT_ROOT / "frontend/src/components/dashboard/accommodation-ai-agent/use-accommodation-agent.ts"


def test_accommodation_fact_options_show_immediate_review_feedback():
    panel_source = AI_PANEL.read_text()
    hook_source = AGENT_HOOK.read_text()
    tab_source = (PROJECT_ROOT / "frontend/src/components/dashboard/accommodation-tab.tsx").read_text()
    checklist_source = (PROJECT_ROOT / "frontend/src/components/dashboard/accommodation-ai-agent/accommodation-checklist.ts").read_text()
    checklist_component_source = (PROJECT_ROOT / "frontend/src/components/dashboard/accommodation-ai-agent/agent-checklist.tsx").read_text()

    assert "togglePendingPatchOption" in hook_source
    assert "applyLocalPatchAnswer" not in hook_source
    assert "_agent_context" in hook_source
    assert "PAGE_AGENT_CONTRACT" in hook_source
    assert "allowed_actions" in hook_source
    assert "patchFromActions" in hook_source
    assert "replaceFieldsFromActions" in hook_source
    assert "pendingReplaceFields" in hook_source
    assert 'action.action === "open_fields"' in hook_source
    assert "requestedEditItemId" in hook_source
    assert "currentItem.status === \"missing\" || currentItem.status === \"in_progress\"" in hook_source
    assert "currentIndex <= nextIndex" in hook_source
    assert "getNextChecklistItem(rebuilt)" in hook_source
    assert "setActiveItemId(next?.id ?? null)" in hook_source
    assert "Ok, ${activeItemId.replace(/_/g, \" \")} added. Next:" not in hook_source
    assert "transitionPromptFor" in hook_source
    assert "const patchedSnapshot = { ...snapshot, ...(pendingPatch || {}) }" in hook_source
    assert "setQuickReplies([])" in hook_source
    assert "Great. The core accommodation facts are complete." in hook_source
    assert "Confirm this public property name is correct:" in hook_source
    assert "Confirm this property type is correct:" in hook_source
    assert "Confirm this capacity is correct:" in hook_source
    assert "Confirm this location is correct:" in hook_source
    assert "Add the city and full address" in hook_source
    assert "Confirm this map pin is correct:" in hook_source
    assert "function preserveIncompleteStatus" in checklist_source
    assert 'const status: AccommodationChecklistStatus = isDone ? "done" : preservedIncompleteStatus ?? "missing"' in checklist_source
    assert 'previous?.status === "draft" ? "draft" : "done"' not in checklist_source
    assert 'profile?.languages || ["hr", "en"]' in tab_source
    assert 'profile?.languages || []' not in tab_source
    assert "max_guests: e.target.value ? Number(e.target.value) : undefined" in tab_source
    assert "number_of_rooms: e.target.value ? Number(e.target.value) : undefined" in tab_source
    assert 'aria-pressed={selectedFactOptions.includes(option)}' in panel_source
    assert "Selected for review:" not in panel_source
    assert "Ready to apply" in panel_source
    assert "border-2 border-emerald-500" in panel_source
    assert "AI Accommodation Assist" in panel_source
    assert "Build a better property profile" in panel_source
    assert "lg:sticky lg:top-3 lg:z-30" in panel_source
    assert "sticky top-2 z-30" not in panel_source
    assert "lg:grid-cols-[280px_minmax(0,1fr)]" in panel_source
    assert "compact" in panel_source
    assert "compact?: boolean" in checklist_component_source
    assert "if (compact)" in checklist_component_source
    assert "xl:grid-cols-[560px_minmax(0,1fr)]" not in tab_source
    assert "PROPERTY_TYPE_OPTIONS" in panel_source
    assert "CAPACITY_OPTIONS" in panel_source
    assert "Name is correct" in panel_source
    assert "Edit name" in panel_source
    assert "patchOptionMatchesSnapshot" in panel_source
    assert "Current type:" in panel_source
    assert "Current capacity:" in panel_source
    assert "Use current coordinates" in panel_source
    assert "Location is correct" in panel_source
    assert "Edit location" in panel_source
    assert "Open matching fields" in panel_source
    assert "parseGuidedFactAnswer" not in panel_source
    assert "visible_options" in panel_source
    assert "selected_options" in panel_source
    assert "actually no pool" in panel_source
    assert "consumeRequestedEdit" in panel_source
    assert "replaceFields: agent.pendingReplaceFields" in panel_source
    assert "compactPatch" in tab_source
    assert "replaceFields.has(\"amenities\")" in tab_source
    assert "COMPOSER_PLACEHOLDER" in panel_source
    assert "Nothing extracted yet" not in panel_source
    assert "rounded-2xl border border-blue-200 bg-white/85 p-3" not in panel_source
