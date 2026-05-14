"""
Commission-based booking service.

Handles direct booking integration, automatic commission tracking,
partner payouts, booking analytics, and multi-currency support.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.partner import Partner, PartnerBooking, BookingStatus, PartnerType
from app.models.guest_group import GuestGroup
from app.models.attraction import Attraction
from app.models.host import Host

logger = logging.getLogger(__name__)


class BookingService:
    """
    Service for managing commission-based bookings.
    
    Handles booking creation, commission calculation, partner payouts,
    and booking analytics with multi-currency support.
    """
    
    # Commission rates (configurable per partner type)
    COMMISSION_RATES = {
        "restaurant": Decimal("0.10"),  # 10%
        "activity": Decimal("0.15"),    # 15%
        "accommodation": Decimal("0.12"), # 12%
        "transport": Decimal("0.10"),    # 10%
        "default": Decimal("0.12")       # 12% default
    }
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the booking service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_booking(
        self,
        guest_group_id: uuid.UUID,
        partner_id: uuid.UUID,
        attraction_id: Optional[uuid.UUID],
        booking_data: Dict[str, Any]
    ) -> Optional[PartnerBooking]:
        """
        Create a new booking with automatic commission calculation.
        
        Args:
            guest_group_id: Guest group making the booking
            partner_id: Partner providing the service
            attraction_id: Optional related attraction
            booking_data: Booking details (amount, currency, date, etc.)
            
        Returns:
            Created booking or None
        """
        try:
            # Get partner
            stmt = select(Partner).where(Partner.id == partner_id)
            result = await self.db.execute(stmt)
            partner = result.scalar_one_or_none()
            
            if not partner:
                logger.error(f"Partner {partner_id} not found")
                return None
            
            # Calculate commission
            booking_amount = Decimal(str(booking_data.get("amount", 0)))
            currency = booking_data.get("currency", "EUR")
            
            # Use partner's commission rate if set, otherwise use default for type
            if partner.commission_rate and partner.commission_rate > 0:
                commission_rate = Decimal(str(partner.commission_rate))
            else:
                partner_type_str = partner.partner_type or "default"
                commission_rate = self.COMMISSION_RATES.get(
                    partner_type_str,
                    self.COMMISSION_RATES["default"]
                )
            
            commission_amount = booking_amount * commission_rate
            
            # Create booking
            booking = PartnerBooking(
                id=uuid.uuid4(),
                guest_group_id=guest_group_id,
                partner_id=partner_id,
                attraction_id=attraction_id,
                host_id=booking_data.get("host_id"),
                
                # Booking details
                booking_reference=booking_data.get("booking_reference"),
                booking_date=booking_data.get("booking_date", datetime.utcnow()),
                service_date=booking_data.get("service_date"),
                
                # Financial details
                booking_amount=float(booking_amount),
                currency=currency,
                commission_rate=float(commission_rate),
                commission_amount=float(commission_amount),
                
                # Status
                status=BookingStatus.PENDING,
                
                # Additional data
                booking_details=booking_data.get("details", {}),
                notes=booking_data.get("notes")
            )
            
            self.db.add(booking)
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Created booking {booking.id} with commission {commission_amount} {currency}")
            return booking
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            await self.db.rollback()
            return None
    
    async def confirm_booking(
        self,
        booking_id: uuid.UUID
    ) -> bool:
        """
        Confirm a booking and mark commission as earned.
        
        Args:
            booking_id: Booking ID to confirm
            
        Returns:
            True if confirmed successfully, False otherwise
        """
        try:
            stmt = select(PartnerBooking).where(PartnerBooking.id == booking_id)
            result = await self.db.execute(stmt)
            booking = result.scalar_one_or_none()
            
            if not booking:
                logger.error(f"Booking {booking_id} not found")
                return False
            
            if booking.status != BookingStatus.PENDING:
                logger.warning(f"Booking {booking_id} is not in pending status")
                return False
            
            # Update status
            booking.status = BookingStatus.CONFIRMED
            booking.confirmed_at = datetime.utcnow()
            booking.commission_status = "earned"
            
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Confirmed booking {booking_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            await self.db.rollback()
            return False
    
    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a booking and handle commission refund.
        
        Args:
            booking_id: Booking ID to cancel
            cancellation_reason: Optional cancellation reason
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            stmt = select(PartnerBooking).where(PartnerBooking.id == booking_id)
            result = await self.db.execute(stmt)
            booking = result.scalar_one_or_none()
            
            if not booking:
                logger.error(f"Booking {booking_id} not found")
                return False
            
            # Update status
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = cancellation_reason
            booking.commission_status = "refunded"
            
            await self.db.commit()
            await self.db.refresh(booking)
            
            logger.info(f"Cancelled booking {booking_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            await self.db.rollback()
            return False
    
    async def get_bookings_for_host(
        self,
        host_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        limit: int = 50
    ) -> List[PartnerBooking]:
        """
        Get all bookings for a host.
        
        Args:
            host_id: Host ID
            status: Optional status filter
            limit: Maximum number of bookings
            
        Returns:
            List of bookings
        """
        try:
            stmt = select(PartnerBooking).where(PartnerBooking.host_id == host_id)
            
            if status:
                stmt = stmt.where(PartnerBooking.status == status)
            
            stmt = stmt.order_by(desc(PartnerBooking.booking_date))
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            bookings = result.scalars().all()
            
            return bookings
            
        except Exception as e:
            logger.error(f"Error getting bookings for host: {e}")
            return []
    
    async def get_bookings_for_partner(
        self,
        partner_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        limit: int = 50
    ) -> List[PartnerBooking]:
        """
        Get all bookings for a partner.
        
        Args:
            partner_id: Partner ID
            status: Optional status filter
            limit: Maximum number of bookings
            
        Returns:
            List of bookings
        """
        try:
            stmt = select(PartnerBooking).where(PartnerBooking.partner_id == partner_id)
            
            if status:
                stmt = stmt.where(PartnerBooking.status == status)
            
            stmt = stmt.order_by(desc(PartnerBooking.booking_date))
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            bookings = result.scalars().all()
            
            return bookings
            
        except Exception as e:
            logger.error(f"Error getting bookings for partner: {e}")
            return []
    
    async def calculate_commission_payout(
        self,
        partner_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate total commission payout for a partner.
        
        Args:
            partner_id: Partner ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Payout calculation details
        """
        try:
            stmt = select(
                func.sum(PartnerBooking.commission_amount).label("total_commission"),
                func.count(PartnerBooking.id).label("total_bookings"),
                PartnerBooking.currency
            ).where(
                and_(
                    PartnerBooking.partner_id == partner_id,
                    PartnerBooking.status == BookingStatus.CONFIRMED,
                    PartnerBooking.commission_status == "earned"
                )
            )
            
            if start_date:
                stmt = stmt.where(PartnerBooking.confirmed_at >= start_date)
            if end_date:
                stmt = stmt.where(PartnerBooking.confirmed_at <= end_date)
            
            stmt = stmt.group_by(PartnerBooking.currency)
            
            result = await self.db.execute(stmt)
            rows = result.all()
            
            payouts = []
            total_all_currencies = {}
            
            for row in rows:
                currency = row.currency
                total_commission = float(row.total_commission or 0)
                total_bookings = row.total_bookings or 0
                
                payouts.append({
                    "currency": currency,
                    "total_commission": total_commission,
                    "total_bookings": total_bookings
                })
                
                total_all_currencies[currency] = total_commission
            
            return {
                "partner_id": str(partner_id),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "payouts_by_currency": payouts,
                "total_all_currencies": total_all_currencies
            }
            
        except Exception as e:
            logger.error(f"Error calculating commission payout: {e}")
            return {
                "partner_id": str(partner_id),
                "error": str(e)
            }
    
    async def get_booking_analytics(
        self,
        host_id: Optional[uuid.UUID] = None,
        partner_id: Optional[uuid.UUID] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get booking analytics and metrics.
        
        Args:
            host_id: Optional host ID filter
            partner_id: Optional partner ID filter
            period_days: Number of days to analyze
            
        Returns:
            Analytics data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            stmt = select(
                func.count(PartnerBooking.id).label("total_bookings"),
                func.sum(PartnerBooking.booking_amount).label("total_revenue"),
                func.sum(PartnerBooking.commission_amount).label("total_commission"),
                func.avg(PartnerBooking.commission_rate).label("avg_commission_rate"),
                PartnerBooking.status,
                PartnerBooking.currency
            ).where(
                PartnerBooking.booking_date >= start_date
            )
            
            if host_id:
                stmt = stmt.where(PartnerBooking.host_id == host_id)
            if partner_id:
                stmt = stmt.where(PartnerBooking.partner_id == partner_id)
            
            stmt = stmt.group_by(PartnerBooking.status, PartnerBooking.currency)
            
            result = await self.db.execute(stmt)
            rows = result.all()
            
            analytics = {
                "period_days": period_days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "by_status": {},
                "by_currency": {},
                "totals": {
                    "total_bookings": 0,
                    "total_revenue": 0,
                    "total_commission": 0
                }
            }
            
            for row in rows:
                status = row.status
                currency = row.currency
                count = row.total_bookings or 0
                revenue = float(row.total_revenue or 0)
                commission = float(row.total_commission or 0)
                
                # By status
                if status not in analytics["by_status"]:
                    analytics["by_status"][status] = {
                        "count": 0,
                        "revenue": 0,
                        "commission": 0
                    }
                
                analytics["by_status"][status]["count"] += count
                analytics["by_status"][status]["revenue"] += revenue
                analytics["by_status"][status]["commission"] += commission
                
                # By currency
                if currency not in analytics["by_currency"]:
                    analytics["by_currency"][currency] = {
                        "count": 0,
                        "revenue": 0,
                        "commission": 0
                    }
                
                analytics["by_currency"][currency]["count"] += count
                analytics["by_currency"][currency]["revenue"] += revenue
                analytics["by_currency"][currency]["commission"] += commission
                
                # Totals
                analytics["totals"]["total_bookings"] += count
                analytics["totals"]["total_revenue"] += revenue
                analytics["totals"]["total_commission"] += commission
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting booking analytics: {e}")
            return {
                "error": str(e)
            }

