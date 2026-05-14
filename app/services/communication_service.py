"""
Automated communication service for guest communications.

Provides automated messaging including:
- Pre-arrival emails
- Welcome kits
- SMS/WhatsApp integration
- Post-stay follow-up
- Multi-language support
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.guest_group import GuestGroup
from app.services.content_generation_service import ContentGenerationService
from app.services.ai_service import AIService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Service for automated guest communications.
    
    Handles pre-arrival emails, welcome kits, SMS/WhatsApp messages,
    and post-stay follow-ups with multi-language support.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the communication service.
        
        Args:
            db: Database session
        """
        self.db = db
        settings_service = SettingsService(db)
        ai_service = AIService(settings_service)
        self.content_service = ContentGenerationService(ai_service, settings_service)
    
    async def send_pre_arrival_email(
        self,
        host: Host,
        guest_group: GuestGroup
    ) -> bool:
        """
        Send pre-arrival email to guests.
        
        Args:
            host: Host instance
            guest_group: Guest group instance
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Generate email content
            email_content = await self.content_service.generate_email_template(
                template_type="pre_arrival",
                host=host,
                guest_group={"group": guest_group},
                language=guest_group.preferred_language or "en"
            )
            
            if not email_content:
                logger.warning(f"Failed to generate pre-arrival email for guest group {guest_group.id}")
                return False
            
            # In production, this would send via email service (SendGrid, AWS SES, etc.)
            logger.info(f"Would send pre-arrival email to {guest_group.lead_guest_email}")
            logger.debug(f"Email content: {email_content[:200]}...")
            
            # Store communication record
            await self._record_communication(
                guest_group_id=guest_group.id,
                communication_type="pre_arrival_email",
                status="sent",
                content=email_content
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending pre-arrival email: {e}")
            return False
    
    async def generate_welcome_kit(
        self,
        host: Host,
        guest_group: GuestGroup
    ) -> Optional[Dict[str, Any]]:
        """
        Generate personalized welcome kit (PDF/document).
        
        Args:
            host: Host instance
            guest_group: Guest group instance
            
        Returns:
            Welcome kit data dictionary or None
        """
        try:
            # Generate welcome email content
            welcome_email = await self.content_service.generate_email_template(
                template_type="welcome",
                host=host,
                guest_group={"group": guest_group},
                language=guest_group.preferred_language or "en"
            )
            
            # Generate local tips
            tips = await self.content_service.generate_local_tips(
                host=host,
                language=guest_group.preferred_language or "en"
            )
            
            # Get recommendations summary
            from app.services.recommendation_service import RecommendationService
            from app.services.ai_service import AIService
            from app.services.settings_service import SettingsService
            
            settings_service = SettingsService(self.db)
            ai_service = AIService(settings_service)
            recommendation_service = RecommendationService(self.db, ai_service)
            
            # Build welcome kit content
            welcome_kit = {
                "host_name": host.name or "Your Host",
                "host_location": f"{host.city}, {host.region or 'Croatia'}",
                "guest_group_name": guest_group.group_name or "Guests",
                "check_in_date": guest_group.check_in_date.isoformat() if guest_group.check_in_date else None,
                "check_out_date": guest_group.check_out_date.isoformat() if guest_group.check_out_date else None,
                "welcome_message": welcome_email or "Welcome to Croatia!",
                "local_tips": tips,
                "emergency_contacts": {
                    "host_phone": host.phone,
                    "host_email": host.email,
                    "emergency_number": "112"  # Croatian emergency number
                },
                "language": guest_group.preferred_language or "en",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Generated welcome kit for guest group {guest_group.id}")
            return welcome_kit
            
        except Exception as e:
            logger.error(f"Error generating welcome kit: {e}")
            return None
    
    async def send_welcome_kit(
        self,
        host: Host,
        guest_group: GuestGroup,
        delivery_method: str = "email"
    ) -> bool:
        """
        Send welcome kit to guests via specified method.
        
        Args:
            host: Host instance
            guest_group: Guest group instance
            delivery_method: Delivery method (email, sms, whatsapp)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Generate welcome kit
            welcome_kit = await self.generate_welcome_kit(host, guest_group)
            
            if not welcome_kit:
                return False
            
            # Send via specified method
            if delivery_method == "email":
                # In production, would send email with PDF attachment
                logger.info(f"Would send welcome kit via email to {guest_group.lead_guest_email}")
            elif delivery_method == "sms":
                # In production, would send SMS with link
                logger.info(f"Would send welcome kit via SMS to {guest_group.lead_guest_phone}")
            elif delivery_method == "whatsapp":
                # In production, would send via WhatsApp API
                logger.info(f"Would send welcome kit via WhatsApp to {guest_group.lead_guest_phone}")
            
            # Record communication
            await self._record_communication(
                guest_group_id=guest_group.id,
                communication_type="welcome_kit",
                status="sent",
                delivery_method=delivery_method
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending welcome kit: {e}")
            return False
    
    async def send_post_stay_follow_up(
        self,
        host: Host,
        guest_group: GuestGroup
    ) -> bool:
        """
        Send post-stay follow-up email requesting feedback.
        
        Args:
            host: Host instance
            guest_group: Guest group instance
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Check if stay is completed
            if guest_group.status != "completed":
                logger.info(f"Guest group {guest_group.id} not completed, skipping follow-up")
                return False
            
            # Generate follow-up email
            email_content = await self.content_service.generate_email_template(
                template_type="follow_up",
                host=host,
                guest_group={"group": guest_group},
                language=guest_group.preferred_language or "en"
            )
            
            if not email_content:
                logger.warning(f"Failed to generate follow-up email for guest group {guest_group.id}")
                return False
            
            # In production, would send via email service
            logger.info(f"Would send follow-up email to {guest_group.lead_guest_email}")
            
            # Record communication
            await self._record_communication(
                guest_group_id=guest_group.id,
                communication_type="post_stay_follow_up",
                status="sent",
                content=email_content
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending post-stay follow-up: {e}")
            return False
    
    async def send_sms(
        self,
        phone_number: str,
        message: str,
        language: str = "en"
    ) -> bool:
        """
        Send SMS message.
        
        Args:
            phone_number: Recipient phone number
            message: Message content
            language: Message language
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # In production, would integrate with SMS service (Twilio, AWS SNS, etc.)
            logger.info(f"Would send SMS to {phone_number}: {message[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    async def send_whatsapp(
        self,
        phone_number: str,
        message: str,
        language: str = "en"
    ) -> bool:
        """
        Send WhatsApp message.
        
        Args:
            phone_number: Recipient phone number
            message: Message content
            language: Message language
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # In production, would integrate with WhatsApp Business API
            logger.info(f"Would send WhatsApp to {phone_number}: {message[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp: {e}")
            return False
    
    async def schedule_communication(
        self,
        guest_group_id: uuid.UUID,
        communication_type: str,
        scheduled_time: datetime,
        data: Dict[str, Any]
    ) -> bool:
        """
        Schedule a communication to be sent at a specific time.
        
        Args:
            guest_group_id: Guest group ID
            communication_type: Type of communication
            scheduled_time: When to send
            data: Communication data
            
        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            # In production, would use a task queue (Celery, RQ, etc.)
            logger.info(f"Scheduled {communication_type} for guest group {guest_group_id} at {scheduled_time}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling communication: {e}")
            return False
    
    async def _record_communication(
        self,
        guest_group_id: uuid.UUID,
        communication_type: str,
        status: str,
        content: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> None:
        """
        Record communication in database for tracking.
        
        Args:
            guest_group_id: Guest group ID
            communication_type: Type of communication
            status: Status (sent, failed, pending)
            content: Optional message content
            delivery_method: Optional delivery method
        """
        try:
            # In production, would store in communications table
            logger.debug(f"Recorded {communication_type} for guest group {guest_group_id}: {status}")
            
        except Exception as e:
            logger.warning(f"Error recording communication: {e}")

