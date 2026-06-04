"""
Host-specific proposed event sources from the discovery agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgresql.connection import Base


class EventSourceProposal(Base):
    __tablename__ = "event_source_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)

    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    proposed_name = Column(String(200), nullable=False)
    proposed_url = Column(String(500), nullable=False)
    source_type = Column(String(50), default="local_office")
    confidence = Column(Float, default=0.5)
    reasoning = Column(Text, nullable=True)
    discovered_by = Column(String(80), default="discovery_agent_v1")
    status = Column(String(20), default="pending")  # pending, approved, rejected

    approved_source_id = Column(UUID(as_uuid=True), ForeignKey("content_sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
