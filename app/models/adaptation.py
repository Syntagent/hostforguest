"""
Adaptation / redesign projects for hosts (indicative planning only).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgresql.connection import Base


class AdaptationProject(Base):
    __tablename__ = "adaptation_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), nullable=True)

    title = Column(String(255), nullable=False)
    brief = Column(Text, nullable=True)
    style_tags = Column(JSON, default=[])
    budget_band = Column(String(20), nullable=True)
    status = Column(String(32), nullable=False, default="draft", index=True)

    assumptions_json = Column(JSON, default={})
    roi_inputs_json = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdaptationAsset(Base):
    __tablename__ = "adaptation_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("adaptation_projects.id"), nullable=False, index=True)
    storage_url = Column(String(1024), nullable=False)
    kind = Column(String(40), nullable=False, default="before_photo")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdaptationProposal(Base):
    __tablename__ = "adaptation_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("adaptation_projects.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    vision_analysis_json = Column(JSON, default={})
    bom_json = Column(JSON, default={})
    concept_image_urls = Column(JSON, default=[])
    total_range_min = Column(Float, nullable=True)
    total_range_max = Column(Float, nullable=True)
    model_ids = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
