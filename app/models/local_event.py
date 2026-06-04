"""
Normalized local events from tourism source scrapers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.postgresql.connection import Base


class LocalEvent(Base):
    """Structured event for guest recommendations and host insights."""

    __tablename__ = "local_events"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_local_events_source_external"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("content_sources.id"), nullable=False, index=True)
    content_update_id = Column(UUID(as_uuid=True), ForeignKey("content_updates.id"), nullable=True)

    external_id = Column(String(200), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, default="")
    url = Column(String(500), nullable=True)
    language = Column(String(10), default="hr")

    start_at = Column(DateTime(timezone=True), nullable=True, index=True)
    end_at = Column(DateTime(timezone=True), nullable=True, index=True)

    city = Column(String(100), nullable=True, index=True)
    region = Column(String(100), nullable=True, index=True)
    venue_name = Column(String(200), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    tags = Column(JSON, default=list)
    status = Column(String(20), default="active")  # active, cancelled, expired
    content_hash = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, default=0.75)

    scraped_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("ContentSource", foreign_keys=[source_id])
