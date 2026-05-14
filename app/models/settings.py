"""
Database models for dynamic configuration and settings.

Stores host-specific API keys, preferences, and configuration in the database.
"""

from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.postgresql.connection import Base


class HostSettings(Base):
    """
    Host-specific settings and API keys stored in database.

    Each host can configure their own AI services, external APIs,
    and platform preferences.
    """

    __tablename__ = "host_settings"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), nullable=False, unique=True)

    # AI Service Configuration - OpenAI
    openai_api_key = Column(Text, nullable=True)
    openai_model = Column(String(100), default="gpt-4o")  # Updated to latest GPT-4o
    openai_alternative_model = Column(String(100), default="gpt-4o-mini")  # For cost-effective tasks

    # Google Gemini AI Configuration
    google_ai_api_key = Column(Text, nullable=True)  # For Gemini API
    gemini_model = Column(String(100), default="gemini-2.5-flash")  # Updated to latest Gemini 2.5 Flash
    gemini_pro_model = Column(String(100), default="gemini-2.5-pro")  # For complex reasoning tasks
    gemini_temperature = Column(String(10), default="0.7")

    # AI Provider Selection (openai, google, both)
    preferred_ai_provider = Column(String(20), default="google")  # Default to Gemini for cost efficiency

    # Embedding Models (OpenAI recommended default)
    embedding_model = Column(String(200), default="text-embedding-3-small")  # OpenAI's latest, most cost-effective
    embedding_large_model = Column(String(200), default="text-embedding-3-large")  # For higher accuracy needs
    embedding_provider = Column(String(50), default="openai")  # openai, google, sentence_transformers
    embedding_dimensions = Column(Integer, default=1536)  # Can be reduced for cost optimization
    embedding_alternative = Column(String(200), default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")  # Fallback

    # Google Services
    google_maps_api_key = Column(Text, nullable=True)
    google_places_api_key = Column(Text, nullable=True)

    # Weather Services
    weather_api_key = Column(Text, nullable=True)
    weather_provider = Column(String(50), default="openweathermap")

    # Croatian Tourism APIs
    croatia_tourism_api_key = Column(Text, nullable=True)
    istria_tourism_api_key = Column(Text, nullable=True)

    # Host Preferences
    default_language = Column(String(10), default="en")
    supported_languages = Column(JSON, default=["en", "hr", "de", "it"])

    # Business Configuration
    commission_rate = Column(String(10), default="10%")
    currency = Column(String(3), default="EUR")

    # AI Behavior Settings
    ai_personality = Column(String(50), default="friendly_local_expert")
    max_recommendations = Column(String(10), default="10")
    recommendation_radius_km = Column(String(10), default="25")

    # Feature Flags
    enable_voice_interface = Column(Boolean, default=True)
    enable_real_time_weather = Column(Boolean, default=True)
    enable_partner_bookings = Column(Boolean, default=True)
    enable_group_analytics = Column(Boolean, default=True)

    # Custom Settings (JSON for flexibility)
    custom_settings = Column(JSON, default={})

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class SystemSettings(Base):
    """
    System-wide settings that apply to all hosts.

    These are platform-level configurations managed by administrators.
    """

    __tablename__ = "system_settings"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), nullable=False, unique=True)
    setting_value = Column(Text, nullable=True)
    setting_type = Column(String(20), default="string")  # string, json, boolean, number

    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")  # ai, external_apis, business, etc.
    is_sensitive = Column(Boolean, default=False)  # For API keys, passwords
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIKeyTemplate(Base):
    """
    Templates for API key configuration.

    Helps hosts understand what API keys they can configure
    and provides setup instructions.
    """

    __tablename__ = "api_key_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # API Information
    service_name = Column(String(100), nullable=False)  # "OpenAI", "Google Maps", etc.
    api_key_field = Column(String(100), nullable=False)  # Field name in HostSettings

    # Configuration
    is_required = Column(Boolean, default=False)
    is_free_tier_available = Column(Boolean, default=True)
    setup_instructions = Column(Text, nullable=True)
    pricing_info = Column(Text, nullable=True)

    # Features enabled by this API
    enables_features = Column(JSON, default=[])  # ["ai_recommendations", "voice_interface"]

    # Metadata
    category = Column(String(50), default="ai")  # ai, maps, weather, tourism
    priority = Column(String(10), default="5")  # 1-10, higher = more important
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# Pydantic models for API requests/responses
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class SettingsCategory(str, Enum):
    """Settings categories."""
    GENERAL = "general"
    NOTIFICATIONS = "notifications"
    RECOMMENDATIONS = "recommendations"
    API_KEYS = "api_keys"
    PRIVACY = "privacy"


class HostSettingsCreate(SQLModel):
    """Host settings creation model."""
    host_id: uuid.UUID
    language_preference: str = "en"
    timezone: str = "Europe/Zagreb"
    currency: str = "EUR"
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    recommendation_settings: Dict[str, Any] = Field(default_factory=dict)
    privacy_settings: Dict[str, Any] = Field(default_factory=dict)


class HostSettingsUpdate(SQLModel):
    """Host settings update model."""
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    recommendation_settings: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None


class HostSettingsResponse(SQLModel):
    """Host settings response model."""
    id: uuid.UUID
    host_id: uuid.UUID
    language_preference: str
    timezone: str
    currency: str
    notification_preferences: Dict[str, Any]
    recommendation_settings: Dict[str, Any]
    privacy_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreate(SQLModel):
    """API key creation model."""
    service_name: str = Field(max_length=100)
    key_value: str = Field(min_length=10)
    description: Optional[str] = None


class APIKeyUpdate(SQLModel):
    """API key update model."""
    key_value: Optional[str] = Field(default=None, min_length=10)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class APIKeyResponse(SQLModel):
    """API key response model (with masked value)."""
    id: uuid.UUID
    host_id: uuid.UUID
    service_name: str
    masked_value: str  # Masked version of the key
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemSettingsResponse(SQLModel):
    """System settings response model."""
    id: uuid.UUID
    setting_key: str
    setting_value: str
    description: Optional[str]
    category: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
