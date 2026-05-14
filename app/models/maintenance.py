"""
Maintenance issues, schedules, and outreach drafts for host properties.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgresql.connection import Base


class MaintenanceIssue(Base):
    __tablename__ = "maintenance_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=True, index=True)

    category = Column(String(80), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    priority = Column(String(20), nullable=False, default="normal")
    photo_urls = Column(JSON, default=[])

    due_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    source = Column(String(40), nullable=False, default="host")
    source_metadata = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), nullable=True)

    title = Column(String(255), nullable=False)
    category = Column(String(80), nullable=False)
    interval_days = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)

    last_run_at = Column(DateTime, nullable=True)
    next_due_at = Column(DateTime, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MaintenanceIssueEvent(Base):
    __tablename__ = "maintenance_issue_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_issues.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class MaintenanceOutreachDraft(Base):
    __tablename__ = "maintenance_outreach_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_issues.id"), nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False, default="whatsapp")
    draft_text = Column(Text, nullable=False)
    host_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
