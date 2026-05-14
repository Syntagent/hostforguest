"""
Channel integration models (Booking.com and future OTAs).

Stores account linkage, property mapping, sync cursors, and idempotent event log.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.postgresql.connection import Base


class ChannelType(str, Enum):
    BOOKING_COM = "booking_com"


class ChannelAccountStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    PENDING = "pending"


class LocalEntityType(str, Enum):
    HOST = "host"
    PARTNER = "partner"


class ChannelEventStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ChannelAccount(Base):
    """Linked OTA account for a host (e.g. Booking.com hotel)."""

    __tablename__ = "channel_accounts"
    __table_args__ = (
        UniqueConstraint("host_id", "channel", name="uq_channel_accounts_host_channel"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)  # booking_com
    status = Column(String(30), default=ChannelAccountStatus.DISCONNECTED, index=True)
    feature_enabled = Column(Boolean, default=True)

    # Booking.com: hotel/property id on the extranet
    external_hotel_id = Column(String(64), nullable=True, index=True)

    # Encrypted credentials (username/password or token), Fernet
    api_username_encrypted = Column(Text, nullable=True)
    api_password_encrypted = Column(Text, nullable=True)

    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelPropertyMapping(Base):
    """Maps a local host or partner row to an external room / rate id."""

    __tablename__ = "channel_property_mappings"
    __table_args__ = (
        Index("ix_channel_map_account_local", "channel_account_id", "local_entity_type", "local_entity_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_account_id = Column(
        UUID(as_uuid=True), ForeignKey("channel_accounts.id"), nullable=False, index=True
    )
    local_entity_type = Column(String(20), nullable=False)  # host | partner
    local_entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    external_room_id = Column(String(64), nullable=True, index=True)
    external_rate_id = Column(String(64), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelSyncState(Base):
    """Per-account sync checkpoints and health."""

    __tablename__ = "channel_sync_states"
    __table_args__ = (UniqueConstraint("channel_account_id", name="uq_channel_sync_account"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_account_id = Column(
        UUID(as_uuid=True), ForeignKey("channel_accounts.id"), nullable=False, index=True
    )
    reservations_cursor = Column(String(512), nullable=True)
    last_reservations_poll_at = Column(DateTime, nullable=True)
    last_availability_push_at = Column(DateTime, nullable=True)
    last_rates_push_at = Column(DateTime, nullable=True)
    last_full_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    consecutive_errors = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelEventLog(Base):
    """Idempotent ingestion / outbound event log."""

    __tablename__ = "channel_event_logs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_channel_event_idempotency"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_account_id = Column(
        UUID(as_uuid=True), ForeignKey("channel_accounts.id"), nullable=False, index=True
    )
    idempotency_key = Column(String(256), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    direction = Column(String(16), nullable=False)  # inbound | outbound
    payload = Column(JSON, default=dict)
    status = Column(String(32), default=ChannelEventStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
