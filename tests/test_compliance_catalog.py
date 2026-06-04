"""Compliance YAML catalog and scenario filtering."""

from pathlib import Path

import pytest

from app.services.compliance_service import (
    get_catalog,
    item_relevance,
    matches_scenarios,
    reload_catalog_for_tests,
)


@pytest.fixture(autouse=True)
def _fresh_catalog():
    reload_catalog_for_tests()
    yield
    reload_catalog_for_tests()


def test_catalog_yaml_exists_and_loads():
    path = Path(__file__).resolve().parents[1] / "infra" / "compliance" / "obligations.hr.yaml"
    assert path.is_file()
    catalog = get_catalog()
    assert catalog.version
    assert len(catalog.categories) >= 4
    assert len(catalog.pdv_regime_rules) >= 3
    assert len(catalog.novasol_regime_rules) >= 3
    assert any(s.id == "in_pdv" for s in catalog.scenarios)
    assert any(s.id == "novasol" for s in catalog.scenarios)


def test_matches_scenarios_always():
    assert matches_scenarios(["always"], {}) is True
    assert matches_scenarios(["in_pdv"], {"in_pdv": True}) is True
    assert matches_scenarios(["in_pdv"], {"in_pdv": False}) is False
    assert matches_scenarios(["uses_ota"], {}) is False


def test_item_relevance_not_applicable_when_no_match():
    rel = item_relevance(["in_pdv"], {"uses_ota": True})
    assert rel == "not_applicable"


def test_item_relevance_optional_when_no_scenarios_selected():
    rel = item_relevance(["in_pdv"], {})
    assert rel == "optional"


def test_novasol_scenario_shows_agency_items():
    catalog = get_catalog()
    novasol_ids = {
        item.id
        for cat in catalog.categories
        if cat.id == "agency_novasol"
        for item in cat.items
    }
    assert "novasol_contract_review" in novasol_ids
    assert matches_scenarios(["novasol"], {"novasol": True})
    assert item_relevance(["novasol"], {"novasol": True}) == "required"
    assert item_relevance(["novasol"], {"uses_ota": True}) == "not_applicable"
