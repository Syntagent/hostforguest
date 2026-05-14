"""
Audit logging service for security and compliance.

Tracks all important actions for security auditing,
compliance, and troubleshooting.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)


class AuditLog:
    """
    Audit log entry model (in-memory for now, can be persisted to DB).
    """
    
    def __init__(
        self,
        action: str,
        user_id: Optional[uuid.UUID],
        resource_type: str,
        resource_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initialize audit log entry.
        
        Args:
            action: Action performed (create, update, delete, view, etc.)
            user_id: User/host ID who performed the action
            resource_type: Type of resource (host, guest_group, attraction, etc.)
            resource_id: ID of the resource
            details: Additional details about the action
            ip_address: IP address of the requester
            user_agent: User agent string
        """
        self.id = uuid.uuid4()
        self.timestamp = datetime.utcnow()
        self.action = action
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent


class AuditService:
    """
    Service for audit logging.
    
    Tracks all important actions for security,
    compliance, and troubleshooting.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize audit service.
        
        Args:
            db: Database session
        """
        self.db = db
        # In-memory audit log (in production, persist to database)
        self.audit_logs: List[AuditLog] = []
    
    async def log_action(
        self,
        action: str,
        user_id: Optional[uuid.UUID],
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log an audit action.
        
        Args:
            action: Action performed
            user_id: User/host ID
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            ip_address: IP address
            user_agent: User agent
        """
        try:
            audit_entry = AuditLog(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Add to in-memory log
            self.audit_logs.append(audit_entry)
            
            # In production, persist to database
            logger.info(
                f"Audit: {action} on {resource_type} {resource_id} by {user_id} "
                f"from {ip_address}"
            )
            
        except Exception as e:
            logger.error(f"Error logging audit action: {e}")
    
    async def get_audit_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            action: Filter by action
            limit: Maximum number of logs
            
        Returns:
            List of audit log entries
        """
        try:
            logs = self.audit_logs.copy()
            
            # Apply filters
            if user_id:
                logs = [log for log in logs if log.user_id == user_id]
            if resource_type:
                logs = [log for log in logs if log.resource_type == resource_type]
            if action:
                logs = [log for log in logs if log.action == action]
            
            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limit results
            logs = logs[:limit]
            
            return [
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []

