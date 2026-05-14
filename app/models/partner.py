"""
Partner model for business partner relationships.

Defines business partners (restaurants, activities, services) that hosts
can partner with, including commission tracking and relationship management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.postgresql.connection import Base


class PartnerType(str, Enum):
    """Types of business partners.

    Cleaning providers: use partner_type=cleaning, or partner_type=service with category=\"cleaning\"
    (see PartnerService._is_cleaning_partner_row). WhatsApp links use phone; optional dedicated
    number in rate_card[\"whatsapp_e164\"] if different from phone.
    """
    RESTAURANT = "restaurant"
    ACTIVITY = "activity"
    TOUR = "tour"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    SERVICE = "service"
    TRADES = "trades"  # majstori / maintenance / crafts
    RETAIL = "retail"  # suppliers, showrooms
    CLEANING = "cleaning"
    OTHER = "other"


class PartnerStatus(str, Enum):
    """Status of a partner relationship."""
    PENDING = "pending"        # Partnership request pending
    ACTIVE = "active"          # Active partnership
    INACTIVE = "inactive"     # Temporarily inactive
    SUSPENDED = "suspended"   # Suspended partnership
    TERMINATED = "terminated" # Partnership terminated


class BookingStatus(str, Enum):
    """Status of a booking."""
    PENDING = "pending"        # Booking created, awaiting confirmation
    CONFIRMED = "confirmed"   # Booking confirmed
    CANCELLED = "cancelled"   # Booking cancelled
    COMPLETED = "completed"  # Service completed
    REFUNDED = "refunded"    # Booking refunded


class Partner(Base):
    """
    Business partner model for Croatian tourist platform.
    
    Represents local businesses (restaurants, activities, tours) that
    hosts can partner with to offer enhanced guest experiences.
    """
    
    __tablename__ = "partners"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    partner_type = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Location Information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True, index=True)
    country = Column(String(50), default="Croatia")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Business Details
    business_hours = Column(JSON, default={})  # Day-specific hours
    price_range = Column(String(50), nullable=True)  # "budget", "moderate", "luxury"
    rate_card = Column(JSON, default=dict)
    price_notes = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=True)  # Maximum capacity
    languages_spoken = Column(JSON, default=[])  # ["hr", "en", "de", "it"]
    
    # Trades / maintenance matching (majstori, suppliers)
    trade_categories = Column(JSON, default=[])  # e.g. ["plumbing", "electrical"]
    emergency_available = Column(Boolean, default=False)

    # Partnership Details
    status = Column(String(20), default=PartnerStatus.PENDING, index=True)
    commission_rate = Column(Float, default=0.10)  # Default 10% commission
    discount_code = Column(String(50), nullable=True, unique=True, index=True)
    discount_percentage = Column(Float, nullable=True)  # Discount for guests
    
    # Performance Metrics
    total_bookings = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    average_rating = Column(Float, nullable=True)
    total_reviews = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)  # When partnership was verified


class HostPartner(Base):
    """
    Relationship between hosts and partners.
    
    Tracks individual host-partner partnerships with specific terms,
    commission rates, and performance metrics.
    """
    
    __tablename__ = "host_partners"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True)
    
    # Partnership Terms
    status = Column(String(20), default=PartnerStatus.PENDING, index=True)
    priority = Column(Integer, default=0)  # Higher priority = recommended first
    commission_rate = Column(Float, nullable=True)  # Override partner default
    custom_discount_code = Column(String(50), nullable=True)
    custom_discount_percentage = Column(Float, nullable=True)
    
    # Partnership Metadata
    partnership_notes = Column(Text, nullable=True)
    partnership_start_date = Column(DateTime, nullable=True)
    partnership_end_date = Column(DateTime, nullable=True)
    
    # Performance Metrics (for this specific host-partner relationship)
    bookings_count = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0.0)
    commission_earned = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PartnerBooking(Base):
    """
    Booking model for partner services.
    
    Tracks bookings made through the platform with automatic
    commission calculation and multi-currency support.
    """

    __tablename__ = "partner_bookings"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships (nullable for OTA-ingested reservations before local guest group exists)
    guest_group_id = Column(UUID(as_uuid=True), ForeignKey("guest_groups.id"), nullable=True, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=True, index=True)
    attraction_id = Column(UUID(as_uuid=True), ForeignKey("attractions.id"), nullable=True, index=True)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=True, index=True)
    
    # Booking Information
    booking_reference = Column(String(100), nullable=True, unique=True, index=True)
    booking_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    service_date = Column(DateTime, nullable=True)  # When the service will be provided
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Financial Details
    booking_amount = Column(Float, nullable=False)  # Total booking amount
    currency = Column(String(10), default="EUR", nullable=False)
    commission_rate = Column(Float, nullable=False)  # Commission rate (e.g., 0.10 for 10%)
    commission_amount = Column(Float, nullable=False)  # Calculated commission
    
    # Status
    status = Column(String(20), default=BookingStatus.PENDING, index=True)
    commission_status = Column(String(20), nullable=True)  # "earned", "refunded", "pending"

    # OTA / channel sync (Booking.com, etc.)
    source_channel = Column(String(50), nullable=True, index=True)
    external_reservation_id = Column(String(128), nullable=True, index=True)
    external_room_id = Column(String(64), nullable=True)
    external_status = Column(String(64), nullable=True)
    external_updated_at = Column(DateTime, nullable=True)
    local_sync_override = Column(Boolean, default=False)  # if True, ignore inbound overwrites
    
    # Additional Information
    booking_details = Column(JSON, default={})  # Additional booking data
    cancellation_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

