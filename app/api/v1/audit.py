"""
Audit logging API endpoints.

Provides REST API for viewing audit logs
for security and compliance purposes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.audit_service import AuditService
from app.api.v1.hosts import get_current_host
from app.models.host import Host

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/logs")
async def get_audit_logs(
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs for the authenticated host only.
    
    Args:
        resource_type: Filter by resource type
        action: Filter by action
        limit: Maximum number of logs
        current_host: Current authenticated host
        db: Database session
        
    Returns:
        List of audit log entries
    """
    try:
        audit_service = AuditService(db)
        
        logs = await audit_service.get_audit_logs(
            user_id=current_host.id,
            resource_type=resource_type,
            action=action,
            limit=limit
        )
        
        return {
            "logs": logs,
            "count": len(logs),
            "filters": {
                "user_id": str(current_host.id),
                "resource_type": resource_type,
                "action": action
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )

