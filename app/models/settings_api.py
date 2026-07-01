"""Settings API response models (frontend TS parity)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class SettingsCategoryResponse(BaseModel):
    """Category-scoped settings slice for GET/PUT /settings/category/{category}."""

    category: str
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    recommendation_settings: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None
    api_keys: Optional[List["SettingsApiKeySummary"]] = None


class SettingsApiKeySummary(BaseModel):
    service_name: str
    masked_value: str
    is_active: bool = True


class SettingsBackupResponse(BaseModel):
    backup_id: uuid.UUID
    host_id: uuid.UUID
    created_at: datetime
    message: str = "Settings backup created"


class SettingsApiKeyValidationResponse(BaseModel):
    valid: bool
    service_name: str
    message: str


class SettingsIntegrationTestResult(BaseModel):
    service_name: str
    configured: bool
    status: str
    message: str


class SettingsIntegrationsTestResponse(BaseModel):
    success: bool
    integrations: List[SettingsIntegrationTestResult] = Field(default_factory=list)


class SystemSettingsListResponse(BaseModel):
    """Read-only system settings bundle for hosts."""

    settings: List[Dict[str, str]] = Field(default_factory=list)
    count: int = 0
