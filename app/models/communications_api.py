"""Communications API response models (frontend TS parity)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CommunicationSuccessResponse(BaseModel):
    success: bool
    message: str


class WelcomeKitEmergencyContacts(BaseModel):
    host_phone: Optional[str] = None
    host_email: Optional[str] = None
    emergency_number: str = "112"


class WelcomeKitContent(BaseModel):
    host_name: str
    host_location: str
    guest_group_name: str
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    welcome_message: str
    local_tips: List[str] = Field(default_factory=list)
    emergency_contacts: WelcomeKitEmergencyContacts
    language: str
    generated_at: str


class WelcomeKitGenerateResponse(BaseModel):
    success: bool
    welcome_kit: WelcomeKitContent
