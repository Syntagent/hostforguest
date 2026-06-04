"""
Host compliance checklist API (Croatian rental obligations).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.hosts import get_current_host
from app.core.database import get_db
from app.models.host import Host
from app.models.host_compliance import (
    ComplianceCatalogResponse,
    ComplianceExplainRequest,
    ComplianceExplainResponse,
    ComplianceItemPatch,
    ComplianceMeResponse,
    ComplianceScenariosUpdate,
)
from app.services.compliance_service import ComplianceService, get_catalog

router = APIRouter()


@router.get("/catalog", response_model=ComplianceCatalogResponse)
async def get_compliance_catalog() -> ComplianceCatalogResponse:
    """Public catalog of obligation items (cache-friendly)."""
    return get_catalog()


@router.get("/me", response_model=ComplianceMeResponse)
async def get_compliance_me(
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
) -> ComplianceMeResponse:
    service = ComplianceService(db)
    return await service.get_me(current_host.id)


@router.put("/me/scenarios", response_model=ComplianceMeResponse)
async def update_compliance_scenarios(
    body: ComplianceScenariosUpdate,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
) -> ComplianceMeResponse:
    service = ComplianceService(db)
    return await service.update_scenarios(current_host.id, body.scenarios)


@router.patch("/me/items/{item_id}", response_model=ComplianceMeResponse)
async def patch_compliance_item(
    item_id: str,
    body: ComplianceItemPatch,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
) -> ComplianceMeResponse:
    service = ComplianceService(db)
    try:
        return await service.patch_item(
            current_host.id,
            item_id,
            body.status,
            body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/me/explain", response_model=ComplianceExplainResponse)
async def explain_compliance(
    body: ComplianceExplainRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
) -> ComplianceExplainResponse:
    service = ComplianceService(db)
    return await service.explain(current_host.id, body.message, body.item_id)
