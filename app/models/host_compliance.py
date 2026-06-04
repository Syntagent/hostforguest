"""
Host compliance checklist models (Croatian rental obligations).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.postgresql.connection import Base

ComplianceItemStatus = Literal["missing", "done", "skipped", "not_applicable"]


class HostComplianceSettings(Base):
    __tablename__ = "host_compliance_settings"

    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"), primary_key=True)
    scenarios = Column(JSONB, nullable=False, default=dict)
    catalog_version = Column(String(32), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HostComplianceItem(Base):
    __tablename__ = "host_compliance_items"

    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(String(64), primary_key=True)
    status = Column(String(20), nullable=False, default="missing")
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceScenarioDef(BaseModel):
    id: str
    label_hr: str


class ComplianceOfficialLink(BaseModel):
    title: str
    url: str


class ComplianceCatalogItem(BaseModel):
    id: str
    label_hr: str
    summary_hr: str
    detail_hr: Optional[str] = None
    applies_when: List[str] = Field(default_factory=list)
    deep_link: Optional[str] = None
    official_links: List[ComplianceOfficialLink] = Field(default_factory=list)
    related_item_ids: List[str] = Field(default_factory=list)


class ComplianceCatalogCategory(BaseModel):
    id: str
    label_hr: str
    items: List[ComplianceCatalogItem] = Field(default_factory=list)


class CompliancePdvRule(BaseModel):
    id: str
    title_hr: str
    body_hr: str


class ComplianceCatalogResponse(BaseModel):
    version: str
    last_reviewed: str
    scenarios: List[ComplianceScenarioDef]
    categories: List[ComplianceCatalogCategory]
    pdv_regime_rules: List[CompliancePdvRule]
    novasol_regime_rules: List[CompliancePdvRule] = Field(default_factory=list)


class ComplianceItemState(BaseModel):
    id: str
    status: ComplianceItemStatus = "missing"
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    relevance: Literal["required", "optional", "not_applicable"] = "required"


class ComplianceMergedItem(ComplianceCatalogItem):
    status: ComplianceItemStatus = "missing"
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    relevance: Literal["required", "optional", "not_applicable"] = "required"


class ComplianceMergedCategory(BaseModel):
    id: str
    label_hr: str
    items: List[ComplianceMergedItem] = Field(default_factory=list)


class ComplianceHints(BaseModel):
    suggest_uses_ota: bool = False
    has_evisitor_records: bool = False


class ComplianceProgress(BaseModel):
    total_relevant: int = 0
    done: int = 0
    percent: int = 0


class ComplianceMeResponse(BaseModel):
    catalog_version: str
    scenarios: Dict[str, bool] = Field(default_factory=dict)
    categories: List[ComplianceMergedCategory] = Field(default_factory=list)
    pdv_regime_rules: List[CompliancePdvRule] = Field(default_factory=list)
    novasol_regime_rules: List[CompliancePdvRule] = Field(default_factory=list)
    progress: ComplianceProgress
    hints: ComplianceHints = Field(default_factory=ComplianceHints)


class ComplianceScenariosUpdate(BaseModel):
    scenarios: Dict[str, bool]


class ComplianceItemPatch(BaseModel):
    status: ComplianceItemStatus
    notes: Optional[str] = Field(None, max_length=4000)


class ComplianceExplainRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    item_id: Optional[str] = Field(None, max_length=64)


class ComplianceExplainResponse(BaseModel):
    answer_hr: str
    suggested_item_ids: List[str] = Field(default_factory=list)
    disclaimer: str
    ai_used: bool = False


class ComplianceExplainAIResult(BaseModel):
    answer_hr: str
    suggested_item_ids: List[str] = Field(default_factory=list)
