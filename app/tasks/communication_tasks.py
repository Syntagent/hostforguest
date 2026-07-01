"""
Background tasks for automated communications.

Handles scheduled communication tasks including:
- Pre-arrival email scheduling
- Welcome kit delivery
- Post-stay follow-up automation
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.guest_group import GuestGroup, GuestGroupStatus
from app.services.communication_service import CommunicationService
from app.services.host_service import HostService
from app.services.rls_service import RLSService

logger = logging.getLogger(__name__)


async def send_scheduled_pre_arrival_emails(db: AsyncSession) -> Dict[str, Any]:
    """
    Send pre-arrival emails for guest groups arriving soon.
    
    Args:
        db: Database session
        
    Returns:
        Task execution results
    """
    try:
        async with RLSService(db).worker_bypass():
            communication_service = CommunicationService(db)
            host_service = HostService(db)
            
            # Find guest groups arriving in next 2-7 days
            today = datetime.utcnow().date()
            start_date = today + timedelta(days=2)
            end_date = today + timedelta(days=7)
            
            stmt = select(GuestGroup).where(
                and_(
                    GuestGroup.status == GuestGroupStatus.ACTIVE,
                    GuestGroup.check_in_date.isnot(None),
                    GuestGroup.check_in_date >= start_date,
                    GuestGroup.check_in_date <= end_date
                )
            )
            
            result = await db.execute(stmt)
            guest_groups = result.scalars().all()
            
            sent_count = 0
            failed_count = 0
            
            for guest_group in guest_groups:
                try:
                    host = await host_service.get_by_id(guest_group.host_id)
                    if host:
                        success = await communication_service.send_pre_arrival_email(host, guest_group)
                        if success:
                            sent_count += 1
                        else:
                            failed_count += 1
                except Exception as e:
                    logger.error(f"Error sending pre-arrival email to {guest_group.id}: {e}")
                    failed_count += 1
            
            return {
                "task": "send_scheduled_pre_arrival_emails",
                "sent": sent_count,
                "failed": failed_count,
                "total": len(guest_groups)
            }
        
    except Exception as e:
        logger.error(f"Error in pre-arrival email task: {e}")
        return {
            "task": "send_scheduled_pre_arrival_emails",
            "error": str(e)
        }


async def send_scheduled_welcome_kits(db: AsyncSession) -> Dict[str, Any]:
    """
    Send welcome kits for guest groups checking in today.
    
    Args:
        db: Database session
        
    Returns:
        Task execution results
    """
    try:
        async with RLSService(db).worker_bypass():
            communication_service = CommunicationService(db)
            host_service = HostService(db)
            
            # Find guest groups checking in today
            today = datetime.utcnow().date()
            
            stmt = select(GuestGroup).where(
                and_(
                    GuestGroup.status == GuestGroupStatus.ACTIVE,
                    GuestGroup.check_in_date == today
                )
            )
            
            result = await db.execute(stmt)
            guest_groups = result.scalars().all()
            
            sent_count = 0
            failed_count = 0
            
            for guest_group in guest_groups:
                try:
                    host = await host_service.get_by_id(guest_group.host_id)
                    if host:
                        success = await communication_service.send_welcome_kit(host, guest_group)
                        if success:
                            sent_count += 1
                        else:
                            failed_count += 1
                except Exception as e:
                    logger.error(f"Error sending welcome kit to {guest_group.id}: {e}")
                    failed_count += 1
            
            return {
                "task": "send_scheduled_welcome_kits",
                "sent": sent_count,
                "failed": failed_count,
                "total": len(guest_groups)
            }
        
    except Exception as e:
        logger.error(f"Error in welcome kit task: {e}")
        return {
            "task": "send_scheduled_welcome_kits",
            "error": str(e)
        }


async def send_scheduled_follow_ups(db: AsyncSession) -> Dict[str, Any]:
    """
    Send follow-up emails for completed guest groups.
    
    Args:
        db: Database session
        
    Returns:
        Task execution results
    """
    try:
        async with RLSService(db).worker_bypass():
            communication_service = CommunicationService(db)
            host_service = HostService(db)
            
            # Find guest groups that completed in last 1-3 days
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=3)
            end_date = today - timedelta(days=1)
            
            stmt = select(GuestGroup).where(
                and_(
                    GuestGroup.status == GuestGroupStatus.COMPLETED,
                    GuestGroup.check_out_date.isnot(None),
                    GuestGroup.check_out_date >= start_date,
                    GuestGroup.check_out_date <= end_date
                )
            )
            
            result = await db.execute(stmt)
            guest_groups = result.scalars().all()
            
            sent_count = 0
            failed_count = 0
            
            for guest_group in guest_groups:
                try:
                    host = await host_service.get_by_id(guest_group.host_id)
                    if host:
                        success = await communication_service.send_post_stay_follow_up(host, guest_group)
                        if success:
                            sent_count += 1
                        else:
                            failed_count += 1
                except Exception as e:
                    logger.error(f"Error sending follow-up to {guest_group.id}: {e}")
                    failed_count += 1
            
            return {
                "task": "send_scheduled_follow_ups",
                "sent": sent_count,
                "failed": failed_count,
                "total": len(guest_groups)
            }
        
    except Exception as e:
        logger.error(f"Error in follow-up task: {e}")
        return {
            "task": "send_scheduled_follow_ups",
            "error": str(e)
        }

