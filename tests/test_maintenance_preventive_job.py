"""Global preventive maintenance job (all hosts) and secured job endpoint."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.host import Host
from app.models.maintenance import MaintenanceSchedule
from app.services.maintenance_service import MaintenanceService


@pytest.mark.asyncio
async def test_run_all_due_schedules_for_all_hosts_creates_issues(db_session):
    h = Host(
        email="preventive-job@example.com",
        hashed_password="x",
        first_name="A",
        last_name="B",
        address="1 St",
        city="Lovran",
        business_type="apartment",
    )
    db_session.add(h)
    await db_session.flush()

    past = datetime.utcnow() - timedelta(days=1)
    s = MaintenanceSchedule(
        host_id=h.id,
        title="Filter",
        category="hvac",
        interval_days=90,
        active=True,
        next_due_at=past,
    )
    db_session.add(s)
    await db_session.commit()

    svc = MaintenanceService(db_session)
    created = await svc.run_all_due_schedules_for_all_hosts()
    assert len(created) == 1
    assert created[0].source == "preventive"
    assert "[Preventive]" in (created[0].title or "")

    # Idempotent for same window: schedule advanced, no second issue
    created2 = await svc.run_all_due_schedules_for_all_hosts()
    assert len(created2) == 0


@pytest.mark.asyncio
async def test_global_job_endpoint_requires_secret(async_client: AsyncClient):
    from app.core.config import settings

    prev = settings.maintenance_job_secret
    settings.maintenance_job_secret = ""
    try:
        r = await async_client.post("/api/v1/maintenance/jobs/run-preventive-global")
        assert r.status_code == 503
    finally:
        settings.maintenance_job_secret = prev


@pytest.mark.asyncio
async def test_global_job_endpoint_runs_with_valid_secret(db_session, async_client: AsyncClient):
    from app.core.config import settings

    h = Host(
        email="job-endpoint@example.com",
        hashed_password="x",
        first_name="A",
        last_name="B",
        address="1 St",
        city="Lovran",
        business_type="apartment",
    )
    db_session.add(h)
    await db_session.flush()
    s = MaintenanceSchedule(
        host_id=h.id,
        title="Boiler",
        category="plumbing",
        interval_days=365,
        active=True,
        next_due_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(s)
    await db_session.commit()

    prev = settings.maintenance_job_secret
    settings.maintenance_job_secret = "unit-test-job-secret"
    try:
        r = await async_client.post(
            "/api/v1/maintenance/jobs/run-preventive-global",
            headers={"X-Maintenance-Job-Secret": "unit-test-job-secret"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["created_count"] == 1
        assert len(data["issues"]) == 1
        assert data["issues"][0]["source"] == "preventive"
    finally:
        settings.maintenance_job_secret = prev
