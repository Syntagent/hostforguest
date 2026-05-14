"""
Partner service for managing business partner relationships.

Handles partner CRUD operations, host-partner relationships,
and commission tracking.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.partner import Partner, HostPartner, PartnerType, PartnerStatus, PartnerBooking, BookingStatus
from app.models.host import Host
from app.db.neo4j.connection import neo4j_manager

logger = logging.getLogger(__name__)


class PartnerService:
    """
    Service for managing business partners and host-partner relationships.
    
    Provides CRUD operations for partners and manages relationships
    in both PostgreSQL and Neo4j.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the partner service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_partner(
        self,
        partner_data: Dict[str, Any]
    ) -> Optional[Partner]:
        """
        Create a new business partner.
        
        Args:
            partner_data: Partner information dictionary
            
        Returns:
            Created Partner or None
        """
        try:
            # Generate discount code if not provided
            if not partner_data.get('discount_code'):
                partner_data['discount_code'] = self._generate_discount_code()
            
            partner = Partner(**partner_data)
            self.db.add(partner)
            await self.db.commit()
            await self.db.refresh(partner)
            
            # Create partner node in Neo4j
            try:
                await neo4j_manager.create_partner_node(
                    partner_id=str(partner.id),
                    partner_data={
                        "name": partner.name,
                        "type": partner.partner_type,
                        "category": partner.category,
                        "city": partner.city,
                        "region": partner.region
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to create Neo4j partner node: {e}")
            
            logger.info(f"Created partner: {partner.id}")
            return partner
            
        except Exception as e:
            logger.error(f"Error creating partner: {e}")
            await self.db.rollback()
            return None
    
    async def get_partner(self, partner_id: uuid.UUID) -> Optional[Partner]:
        """
        Get a partner by ID.
        
        Args:
            partner_id: Partner UUID
            
        Returns:
            Partner or None
        """
        try:
            stmt = select(Partner).where(Partner.id == partner_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting partner: {e}")
            return None
    
    async def list_partners(
        self,
        city: Optional[str] = None,
        partner_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Partner]:
        """
        List partners with optional filters.
        
        Args:
            city: Filter by city
            partner_type: Filter by partner type
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of partners
        """
        try:
            stmt = select(Partner)
            
            if city:
                stmt = stmt.where(Partner.city == city)
            if partner_type:
                stmt = stmt.where(Partner.partner_type == partner_type)
            if status:
                stmt = stmt.where(Partner.status == status)
            
            stmt = stmt.order_by(desc(Partner.total_bookings), desc(Partner.average_rating))
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error listing partners: {e}")
            return []
    
    async def create_host_partner_relationship(
        self,
        host_id: uuid.UUID,
        partner_id: uuid.UUID,
        relationship_data: Optional[Dict[str, Any]] = None
    ) -> Optional[HostPartner]:
        """
        Create a relationship between a host and partner.
        
        Args:
            host_id: Host UUID
            partner_id: Partner UUID
            relationship_data: Optional relationship metadata
            
        Returns:
            Created HostPartner relationship or None
        """
        try:
            # Check if relationship already exists
            stmt = select(HostPartner).where(
                and_(
                    HostPartner.host_id == host_id,
                    HostPartner.partner_id == partner_id
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Host-partner relationship already exists: {host_id} -> {partner_id}")
                return existing
            
            # Create new relationship
            relationship_data = relationship_data or {}
            host_partner = HostPartner(
                host_id=host_id,
                partner_id=partner_id,
                **relationship_data
            )
            
            self.db.add(host_partner)
            await self.db.commit()
            await self.db.refresh(host_partner)
            
            # Create relationship in Neo4j
            try:
                await neo4j_manager.create_host_partner_relationship(
                    host_id=str(host_id),
                    partner_id=str(partner_id),
                    relationship_data={
                        "priority": relationship_data.get("priority", 0),
                        "commission_rate": relationship_data.get("commission_rate"),
                        "status": relationship_data.get("status", "active")
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to create Neo4j relationship: {e}")
            
            logger.info(f"Created host-partner relationship: {host_id} -> {partner_id}")
            return host_partner
            
        except Exception as e:
            logger.error(f"Error creating host-partner relationship: {e}")
            await self.db.rollback()
            return None
    
    async def get_host_partners(
        self,
        host_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all partners for a host.
        
        Args:
            host_id: Host UUID
            
        Returns:
            List of partner data with relationship info
        """
        try:
            # Get from PostgreSQL
            stmt = select(HostPartner, Partner).join(
                Partner, HostPartner.partner_id == Partner.id
            ).where(
                HostPartner.host_id == host_id
            ).order_by(
                desc(HostPartner.priority),
                desc(Partner.total_bookings)
            )
            
            result = await self.db.execute(stmt)
            rows = result.all()
            
            partners = []
            for host_partner, partner in rows:
                partners.append({
                    "partner": partner,
                    "relationship": host_partner,
                    "priority": host_partner.priority,
                    "commission_rate": host_partner.commission_rate or partner.commission_rate,
                    "status": host_partner.status
                })
            return partners
            
        except Exception as e:
            logger.error(f"Error getting host partners: {e}")
            return []
    
    def _generate_discount_code(self) -> str:
        """
        Generate a unique discount code.
        
        Returns:
            Discount code string
        """
        import secrets
        import string
        
        # Generate 8-character alphanumeric code
        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        return f"TGL{code}"
    
    async def update_partner(
        self,
        partner_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> Optional[Partner]:
        """
        Update a partner.
        
        Args:
            partner_id: Partner UUID
            update_data: Fields to update
            
        Returns:
            Updated Partner or None
        """
        try:
            stmt = update(Partner).where(
                Partner.id == partner_id
            ).values(
                **update_data,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Refresh and return
            return await self.get_partner(partner_id)
            
        except Exception as e:
            logger.error(f"Error updating partner: {e}")
            await self.db.rollback()
            return None
    
    async def update_host_partner_relationship(
        self,
        host_id: uuid.UUID,
        partner_id: uuid.UUID,
        update_data: Dict[str, Any]
    ) -> Optional[HostPartner]:
        """
        Update a host-partner relationship.
        
        Args:
            host_id: Host UUID
            partner_id: Partner UUID
            update_data: Fields to update
            
        Returns:
            Updated HostPartner or None
        """
        try:
            stmt = update(HostPartner).where(
                and_(
                    HostPartner.host_id == host_id,
                    HostPartner.partner_id == partner_id
                )
            ).values(
                **update_data,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Update Neo4j relationship
            try:
                await neo4j_manager.create_host_partner_relationship(
                    host_id=str(host_id),
                    partner_id=str(partner_id),
                    relationship_data=update_data
                )
            except Exception as e:
                logger.warning(f"Failed to update Neo4j relationship: {e}")
            
            # Get and return updated relationship
            stmt = select(HostPartner).where(
                and_(
                    HostPartner.host_id == host_id,
                    HostPartner.partner_id == partner_id
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error updating host-partner relationship: {e}")
            await self.db.rollback()
            return None



    def _is_cleaning_partner_row(self, partner: Partner) -> bool:
        pt = (partner.partner_type or '').lower()
        cat = (partner.category or '').lower()
        if pt == PartnerType.CLEANING.value:
            return True
        if pt == PartnerType.SERVICE.value and cat == 'cleaning':
            return True
        tc = partner.trade_categories or []
        if isinstance(tc, list) and 'cleaning' in [str(x).lower() for x in tc]:
            return True
        return False

    async def list_cleaning_partners(
        self,
        city: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> List[Partner]:
        try:
            stmt = select(Partner).where(Partner.status == PartnerStatus.ACTIVE)
            conds = []
            if city and city.strip():
                conds.append(func.lower(Partner.city) == city.strip().lower())
            if region and region.strip():
                conds.append(func.lower(Partner.region) == region.strip().lower())
            if conds:
                stmt = stmt.where(or_(*conds))
            stmt = stmt.where(
                or_(
                    Partner.partner_type == PartnerType.CLEANING.value,
                    and_(
                        Partner.partner_type == PartnerType.SERVICE.value,
                        func.lower(Partner.category) == 'cleaning',
                    ),
                )
            )
            stmt = stmt.order_by(desc(Partner.average_rating), desc(Partner.total_bookings))
            stmt = stmt.limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error('Error listing cleaning partners: %s', e)
            return []

    async def remove_host_partner(self, host_id: uuid.UUID, partner_id: uuid.UUID) -> bool:
        try:
            from sqlalchemy import delete
            stmt = delete(HostPartner).where(
                and_(HostPartner.host_id == host_id, HostPartner.partner_id == partner_id)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error('Error removing host partner: %s', e)
            await self.db.rollback()
            return False

    async def create_cleaning_booking(
        self,
        host_id: uuid.UUID,
        partner_id: uuid.UUID,
        service_date: Optional[datetime] = None,
        guest_group_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        intent: str = 'turnover',
        estimated_amount: float = 0.0,
        currency: str = 'EUR',
    ) -> Optional[PartnerBooking]:
        partner = await self.get_partner(partner_id)
        if not partner or not self._is_cleaning_partner_row(partner):
            return None
        details: Dict[str, Any] = {
            'kind': 'cleaning',
            'intent': intent,
        }
        if guest_group_id:
            details['guest_group_id'] = str(guest_group_id)
        try:
            booking = PartnerBooking(
                host_id=host_id,
                partner_id=partner_id,
                guest_group_id=guest_group_id,
                service_date=service_date,
                booking_amount=float(estimated_amount),
                currency=currency,
                commission_rate=0.0,
                commission_amount=0.0,
                status=BookingStatus.PENDING,
                notes=notes,
                booking_details=details,
            )
            self.db.add(booking)
            await self.db.commit()
            await self.db.refresh(booking)
            return booking
        except Exception as e:
            logger.error('Error creating cleaning booking: %s', e)
            await self.db.rollback()
            return None

    async def list_host_cleaning_bookings(self, host_id: uuid.UUID, limit: int = 50) -> List[PartnerBooking]:
        try:
            stmt = (
                select(PartnerBooking)
                .where(PartnerBooking.host_id == host_id)
                .order_by(desc(PartnerBooking.created_at))
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = list(result.scalars().all())
            return [b for b in rows if (b.booking_details or {}).get('kind') == 'cleaning']
        except Exception as e:
            logger.error('Error listing cleaning bookings: %s', e)
            return []

    async def get_cleaning_booking_for_host(
        self, booking_id: uuid.UUID, host_id: uuid.UUID
    ) -> Optional[PartnerBooking]:
        stmt = select(PartnerBooking).where(
            and_(PartnerBooking.id == booking_id, PartnerBooking.host_id == host_id)
        )
        result = await self.db.execute(stmt)
        b = result.scalar_one_or_none()
        if not b or (b.booking_details or {}).get('kind') != 'cleaning':
            return None
        return b

    async def update_cleaning_booking_status(
        self, booking_id: uuid.UUID, host_id: uuid.UUID, new_status: str
    ) -> Optional[PartnerBooking]:
        b = await self.get_cleaning_booking_for_host(booking_id, host_id)
        if not b:
            return None
        try:
            b.status = new_status
            if new_status == BookingStatus.CONFIRMED.value:
                b.confirmed_at = datetime.utcnow()
            if new_status == BookingStatus.CANCELLED.value:
                b.cancelled_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(b)
            return b
        except Exception as e:
            logger.error('Error updating booking status: %s', e)
            await self.db.rollback()
            return None

    async def submit_cleaning_booking_feedback(
        self,
        booking_id: uuid.UUID,
        host_id: uuid.UUID,
        rating: int,
        comment: Optional[str] = None,
    ) -> Optional[PartnerBooking]:
        if rating < 1 or rating > 5:
            return None
        b = await self.get_cleaning_booking_for_host(booking_id, host_id)
        if not b or b.status != BookingStatus.COMPLETED.value:
            return None
        details = dict(b.booking_details or {})
        if details.get('host_feedback'):
            return None
        details['host_feedback'] = {
            'rating': rating,
            'comment': (comment or '')[:2000],
            'created_at': datetime.utcnow().isoformat() + 'Z',
        }
        try:
            b.booking_details = details
            await self.db.commit()
            await self.db.refresh(b)
            if b.partner_id:
                await self._rollup_partner_rating(b.partner_id, rating)
            return b
        except Exception as e:
            logger.error('Error saving cleaning feedback: %s', e)
            await self.db.rollback()
            return None

    async def _rollup_partner_rating(self, partner_id: uuid.UUID, new_rating: int) -> None:
        p = await self.get_partner(partner_id)
        if not p:
            return
        n = int(p.total_reviews or 0)
        old = p.average_rating
        if old is None:
            p.average_rating = float(new_rating)
        else:
            p.average_rating = round((float(old) * n + new_rating) / (n + 1), 2)
        p.total_reviews = n + 1
        await self.db.commit()
