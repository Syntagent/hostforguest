"""Regression tests for event scraper HTTP policy."""

from __future__ import annotations

import pytest

from app.scraping.events.policies import PoliteCrawlerConfig

pytestmark = pytest.mark.no_db


def test_polite_crawler_retries_blocking_status_codes():
    config = PoliteCrawlerConfig()

    assert 403 in config.retry_statuses
    assert 429 in config.retry_statuses
    assert 503 in config.retry_statuses


def test_polite_crawler_uses_browser_user_agent_by_default():
    config = PoliteCrawlerConfig()

    assert "Mozilla/5.0" in config.user_agent
    assert "HostForGuest" not in config.user_agent
