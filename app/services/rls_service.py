"""
Row-Level Security (RLS) service for PostgreSQL.

Manages RLS policies and sets tenant context
for database queries.
"""

import logging
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RLSService:
    """
    Service for managing Row-Level Security.
    
    Sets tenant context for database queries to ensure
    data isolation between hosts.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize RLS service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def set_host_context(
        self,
        host_id: uuid.UUID
    ) -> bool:
        """
        Set current host context for RLS.
        
        Args:
            host_id: Host ID to set as current context
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            # Set PostgreSQL session variable for RLS
            stmt = text("SELECT set_config('app.current_host_id', :host_id, false)")
            await self.db.execute(stmt, {"host_id": str(host_id)})
            await self.db.commit()
            
            logger.debug(f"Set RLS context for host {host_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting RLS context: {e}")
            await self.db.rollback()
            return False
    
    async def clear_host_context(self) -> bool:
        """
        Clear current host context.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            stmt = text("SELECT set_config('app.current_host_id', '', false)")
            await self.db.execute(stmt)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing RLS context: {e}")
            await self.db.rollback()
            return False

