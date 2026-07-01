"""
Adaptation / redesign studio API (indicative only).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.host import Host
from app.api.v1.hosts import get_current_host
from app.services.adaptation_service import AdaptationProjectService, AdaptationAIService

router = APIRouter()


class AdaptationProjectCreate(BaseModel):
    title: str = Field(..., max_length=255)
    brief: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    budget_band: Optional[str] = Field(None, max_length=20)


class AdaptationProjectPatch(BaseModel):
    title: Optional[str] = None
    brief: Optional[str] = None
    style_tags: Optional[List[str]] = None
    budget_band: Optional[str] = None
    status: Optional[str] = None
    roi_inputs_json: Optional[Dict[str, Any]] = None
    assumptions_json: Optional[Dict[str, Any]] = None
    documentation_notes: Optional[str] = Field(None, max_length=20000)


class AdaptationAssetCreate(BaseModel):
    storage_url: str = Field(..., max_length=1024)
    kind: str = "before_photo"
    sort_order: int = 0


class BOMPatchBody(BaseModel):
    lines: List[Dict[str, Any]]


class SupplierSuggestBody(BaseModel):
    bom_category: str = "other"


class AdaptationAssistantHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=6000)


class AdaptationAssistantBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: List[AdaptationAssistantHistoryItem] = Field(default_factory=list, max_length=12)


class AdaptationRoiResultResponse(BaseModel):
    baseline_nights_year: float
    baseline_revenue_year: float
    projected_revenue_year: float
    incremental_revenue_year: float
    incremental_revenue_month: float
    simple_payback_months: Optional[float] = None
    disclaimer: str


class AdaptationProjectResponse(BaseModel):
    id: str
    title: str
    brief: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    budget_band: Optional[str] = None
    status: str
    assumptions_json: Dict[str, Any] = Field(default_factory=dict)
    roi_inputs_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdaptationProjectListResponse(BaseModel):
    projects: List[AdaptationProjectResponse]


class AdaptationAssetResponse(BaseModel):
    id: str
    project_id: str
    storage_url: str
    kind: str
    sort_order: int


class AdaptationAnalyzeResponse(BaseModel):
    proposal_id: str
    version: int
    vision_analysis: Dict[str, Any] = Field(default_factory=dict)
    bom: Dict[str, Any] = Field(default_factory=dict)
    total_range_min: Optional[float] = None
    total_range_max: Optional[float] = None
    roi_preview: AdaptationRoiResultResponse
    disclaimer: str
    ai_used: bool
    bom_source: str
    hints: Optional[List[str]] = None
    vision_multimodal: Optional[bool] = None
    vision_images_fetched: Optional[int] = None
    vision_images_requested: Optional[int] = None
    vision_ai_provider: Optional[str] = None


class AdaptationPhaseResponse(BaseModel):
    phase_name: str = ""
    description: str = ""
    order: int = 1
    duration_weeks_min: int = 0
    duration_weeks_max: int = 0
    key_tasks: List[str] = Field(default_factory=list)


class AdaptationAssistantResponse(BaseModel):
    disclaimer: str
    ai_used: bool
    reply: str
    phases: List[AdaptationPhaseResponse] = Field(default_factory=list)
    cost_orientation: str = ""
    timeline_overview: str = ""
    communication_tips: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)


class AdaptationSupplierPartnerResponse(BaseModel):
    partner_id: str
    name: str
    phone: Optional[str] = None
    city: str
    distance_km: Optional[float] = None


class AdaptationSupplierDiscoveryResponse(BaseModel):
    host_has_coordinates: bool
    any_distance_unknown: bool
    linked_only: bool = True
    sort_explanation: str


class AdaptationSupplierSuggestResponse(BaseModel):
    bom_category: str
    maintenance_category: str
    partners: List[AdaptationSupplierPartnerResponse] = Field(default_factory=list)
    discovery: AdaptationSupplierDiscoveryResponse


class AdaptationBomPatchResponse(BaseModel):
    bom: Dict[str, Any]
    total_range_min: float
    total_range_max: float


class AdaptationProposalSummaryResponse(BaseModel):
    id: str
    version: int
    vision_analysis_json: Optional[Dict[str, Any]] = None
    bom_json: Optional[Dict[str, Any]] = None
    concept_image_urls: List[str] = Field(default_factory=list)
    total_range_min: Optional[float] = None
    total_range_max: Optional[float] = None
    created_at: Optional[str] = None


class AdaptationProposalListResponse(BaseModel):
    proposals: List[AdaptationProposalSummaryResponse]


def _proj_dict(p) -> Dict[str, Any]:
    return {
        "id": str(p.id),
        "title": p.title,
        "brief": p.brief,
        "style_tags": p.style_tags or [],
        "budget_band": p.budget_band,
        "status": p.status,
        "assumptions_json": p.assumptions_json or {},
        "roi_inputs_json": p.roi_inputs_json or {},
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/projects", response_model=AdaptationProjectListResponse)
async def list_projects(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    rows = await svc.list_projects(current_host.id)
    return {"projects": [_proj_dict(p) for p in rows]}


@router.post("/projects", status_code=status.HTTP_201_CREATED, response_model=AdaptationProjectResponse)
async def create_project(
    body: AdaptationProjectCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    p = await svc.create_project(
        current_host.id,
        title=body.title,
        brief=body.brief,
        style_tags=body.style_tags,
        budget_band=body.budget_band,
    )
    return _proj_dict(p)


@router.get("/projects/{project_id}", response_model=AdaptationProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    p = await svc.get_project(current_host.id, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return _proj_dict(p)


@router.patch("/projects/{project_id}", response_model=AdaptationProjectResponse)
async def patch_project(
    project_id: uuid.UUID,
    body: AdaptationProjectPatch,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    data = body.model_dump(exclude_unset=True)
    p = await svc.update_project(current_host.id, project_id, **data)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return _proj_dict(p)


@router.post(
    "/projects/{project_id}/assets",
    status_code=status.HTTP_201_CREATED,
    response_model=AdaptationAssetResponse,
)
async def add_asset(
    project_id: uuid.UUID,
    body: AdaptationAssetCreate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    a = await svc.add_asset(
        current_host.id,
        project_id,
        storage_url=body.storage_url,
        kind=body.kind,
        sort_order=body.sort_order,
    )
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "storage_url": a.storage_url,
        "kind": a.kind,
        "sort_order": a.sort_order,
    }


@router.post("/projects/{project_id}/assistant", response_model=AdaptationAssistantResponse)
async def adaptation_assistant(
    project_id: uuid.UUID,
    body: AdaptationAssistantBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    AI coach for Adaptation studio: project path (phases), indicative costs/time, contractor communication.
    """
    psvc = AdaptationProjectService(db)
    p = await psvc.get_project(current_host.id, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    ai = AdaptationAIService(db)
    hist = [h.model_dump() for h in body.history]
    return await ai.assistant_turn(current_host, p, body.message.strip(), hist)


@router.post("/projects/{project_id}/analyze", response_model=AdaptationAnalyzeResponse)
async def analyze_project(
    project_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    psvc = AdaptationProjectService(db)
    p = await psvc.get_project(current_host.id, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    ai = AdaptationAIService(db)
    return await ai.analyze_project(current_host, p)


@router.post(
    "/projects/{project_id}/suggest-suppliers",
    response_model=AdaptationSupplierSuggestResponse,
)
async def suggest_suppliers(
    project_id: uuid.UUID,
    body: SupplierSuggestBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    psvc = AdaptationProjectService(db)
    p = await psvc.get_project(current_host.id, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    ai = AdaptationAIService(db)
    return await ai.suggest_suppliers(current_host, p, body.bom_category)


@router.patch("/projects/{project_id}/bom", response_model=AdaptationBomPatchResponse)
async def patch_bom(
    project_id: uuid.UUID,
    body: BOMPatchBody,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    out = await svc.patch_bom(current_host.id, project_id, body.lines)
    if not out:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return out


@router.get("/projects/{project_id}/roi", response_model=AdaptationRoiResultResponse)
async def get_roi(
    project_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    p = await svc.get_project(current_host.id, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return svc.compute_roi_for_project(p)


@router.get("/projects/{project_id}/proposals", response_model=AdaptationProposalListResponse)
async def list_proposals(
    project_id: uuid.UUID,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    svc = AdaptationProjectService(db)
    rows = await svc.list_proposals(current_host.id, project_id)
    return {
        "proposals": [
            {
                "id": str(x.id),
                "version": x.version,
                "vision_analysis_json": x.vision_analysis_json,
                "bom_json": x.bom_json,
                "concept_image_urls": x.concept_image_urls or [],
                "total_range_min": x.total_range_min,
                "total_range_max": x.total_range_max,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in rows
        ]
    }
