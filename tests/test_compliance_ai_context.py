"""Compliance AI explain uses full context, not keyword routing."""

import uuid

import pytest

from app.models.host_compliance import ComplianceExplainAIResult
from app.services.compliance_service import ComplianceService, DISCLAIMER_HR


@pytest.mark.asyncio
async def test_explain_builds_context_from_checklist(db_session, monkeypatch):
    from app.services.compliance_service import get_catalog
    from tests.conftest import create_test_host_async

    host = await create_test_host_async(db_session, f"compliance-ai-{uuid.uuid4().hex[:10]}@example.com")
    svc = ComplianceService(db_session)

    catalog = get_catalog()
    item_id = catalog.categories[0].items[0].id
    await svc.update_scenarios(host.id, {"in_pdv": True})
    await svc.patch_item(host.id, item_id, "done", None)

    captured: dict = {}

    async def fake_structured(self, host_id, messages, *args, **kwargs):
        captured["host_id"] = host_id
        captured["messages"] = messages
        captured["context"] = kwargs.get("context")
        return {
            "success": True,
            "structured_data": ComplianceExplainAIResult(
                answer_hr="Test odgovor o PDV-u.",
                suggested_item_ids=[item_id],
            ),
        }

    from app.services.ai_service_fallback import AIServiceWithFallback

    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", fake_structured)

    out = await svc.explain(host.id, "Što trebam za PDV preko Bookinga?", item_id)
    assert out.ai_used is True
    assert "Test odgovor" in out.answer_hr
    assert DISCLAIMER_HR in out.disclaimer
    assert isinstance(captured.get("messages"), list)
    user_blob = str(captured["messages"])
    assert "PDV" in user_blob or "checkliste" in user_blob.lower() or item_id in user_blob
    assert captured.get("context", {}).get("task") == "compliance_explain"


@pytest.mark.asyncio
async def test_explain_fallback_without_ai(db_session, monkeypatch):
    from tests.conftest import create_test_host_async

    host = await create_test_host_async(db_session, f"compliance-fb-{uuid.uuid4().hex[:10]}@example.com")
    svc = ComplianceService(db_session)

    async def fail_structured(self, *args, **kwargs):
        return {"success": False}

    from app.services.ai_service_fallback import AIServiceWithFallback

    monkeypatch.setattr(AIServiceWithFallback, "generate_structured_response", fail_structured)

    out = await svc.explain(host.id, "Pitanje?", "evisitor_registration")
    assert out.ai_used is False
    assert out.answer_hr
