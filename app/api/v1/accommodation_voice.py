"""Voice ingestion for Stay-tab accommodation assist — transcribe then run the text agent."""

import base64
import json
import os
import struct
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.host_onboarding_models import (
    AccommodationAgentMessageResponse,
    AccommodationPatch,
    AccommodationSnapshot,
    AgentMessage,
    ChecklistItemState,
)
from app.core.database import get_db
from app.api.v1.hosts import get_current_host
from app.models.host import Host, HostProfile
from app.services.host_onboarding_service import HostOnboardingService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/onboarding/accommodation/voice", tags=["accommodation-voice"])

_PATCH_FIELD_KEYS = frozenset(AccommodationPatch.model_fields.keys())


class VoiceIngestRequest(BaseModel):
    """Transcribed text and/or raw audio for the same agent pipeline as typed messages."""

    message: Optional[str] = Field(None, description="Client transcript when browser STT is available")
    audio_base64: Optional[str] = Field(None, description="16-bit LE mono PCM when server must transcribe")
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    focused_item_id: Optional[str] = None
    checklist_state: List[ChecklistItemState] = Field(default_factory=list)
    accommodation_snapshot: AccommodationSnapshot = Field(default_factory=AccommodationSnapshot)
    conversation_history: List[AgentMessage] = Field(default_factory=list)


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap 16-bit LE mono PCM in a minimal WAV container for Gemini."""
    if not pcm_bytes:
        return b""
    channels = 1
    bits = 16
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8
    data_size = len(pcm_bytes)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data",
        data_size,
    )
    return header + pcm_bytes


async def _get_google_api_key(db: AsyncSession, host_id: uuid.UUID) -> Optional[str]:
    settings = SettingsService(db)
    api_key = await settings.get_host_api_key(str(host_id), "google_ai")
    return api_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")


async def _transcribe_pcm(api_key: str, pcm_bytes: bytes, sample_rate: int) -> str:
    from google import genai
    from google.genai import types

    if len(pcm_bytes) < 3200:
        raise ValueError("Audio too short — speak a full sentence and try again.")
    wav = _pcm_to_wav(pcm_bytes, sample_rate)
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    model_id = os.environ.get("GEMINI_TRANSCRIBE_MODEL", "gemini-2.0-flash")
    response = client.models.generate_content(
        model=model_id,
        contents=[
            types.Content(
                parts=[
                    types.Part.from_bytes(data=wav, mime_type="audio/wav"),
                    types.Part(
                        text=(
                            "Transcribe exactly what the accommodation host said. "
                            "Return only the transcript text, no commentary."
                        )
                    ),
                ]
            )
        ],
    )
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise ValueError("Could not understand the recording — try again closer to the microphone.")
    return text


def _snapshot_from_db(host: Host, profile: Optional[HostProfile]) -> AccommodationSnapshot:
    """Build typed profile snapshot from host + profile rows (all AccommodationPatch fields)."""
    raw_rules = getattr(profile, "property_rules", None) if profile else None
    property_rules = dict(raw_rules) if isinstance(raw_rules, dict) else None
    return AccommodationSnapshot(
        property_name=getattr(profile, "property_name", None) if profile else None,
        property_type=getattr(profile, "property_type", None) if profile else None,
        max_guests=getattr(profile, "max_guests", None) if profile else None,
        number_of_rooms=getattr(profile, "number_of_rooms", None) if profile else None,
        city=(getattr(profile, "city", None) if profile else None) or host.city,
        county=(getattr(profile, "county", None) if profile else None) or host.county,
        address=getattr(profile, "address", None) if profile else None,
        latitude=getattr(profile, "latitude", None) if profile else None,
        longitude=getattr(profile, "longitude", None) if profile else None,
        location_story=getattr(profile, "location_story", None) if profile else None,
        welcome_message=host.welcome_message,
        amenities=list(getattr(profile, "amenities", None) or []),
        services_offered=list(getattr(profile, "services_offered", None) or []),
        expertise_areas=list(getattr(profile, "expertise_areas", None) or []),
        languages=list(host.languages or []),
        gallery_images=list(getattr(profile, "gallery_images", None) or []),
        property_rules=property_rules,
    )


async def _load_db_snapshot(db: AsyncSession, host: Host) -> AccommodationSnapshot:
    profile = (await db.execute(select(HostProfile).where(HostProfile.host_id == host.id))).scalar_one_or_none()
    return _snapshot_from_db(host, profile)


def _merge_snapshot(db_snapshot: AccommodationSnapshot, client_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    merged = db_snapshot.to_agent_dict()
    if isinstance(client_snapshot, dict):
        for key, value in client_snapshot.items():
            if key.startswith("_"):
                continue
            if key in _PATCH_FIELD_KEYS and _is_meaningful(value):
                merged[key] = value
    return merged


@router.get("/health")
async def accommodation_voice_health():
    return {"status": "ok", "service": "accommodation-voice-ingest"}


@router.post("/ingest", response_model=AccommodationAgentMessageResponse)
async def accommodation_voice_ingest(
    request: VoiceIngestRequest,
    current_host: Host = Depends(get_current_host),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest host speech into the accommodation onboarding agent (same path as typed chat).

    Returns a reviewable suggested_patch — nothing is saved until the host clicks Apply.
    """
    api_key = await _get_google_api_key(db, current_host.id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google AI key missing")

    transcript = (request.message or "").strip()
    if not transcript:
        if not request.audio_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide message text or audio_base64",
            )
        try:
            pcm = base64.b64decode(request.audio_base64)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audio payload") from exc
        try:
            transcript = await _transcribe_pcm(api_key, pcm, request.sample_rate)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Transcription failed: {exc}",
            ) from exc

    db_snapshot = await _load_db_snapshot(db, current_host)
    client_snapshot = request.accommodation_snapshot.to_agent_dict()
    snapshot = _merge_snapshot(db_snapshot, client_snapshot)
    agent_context = client_snapshot.get("_agent_context")
    if not isinstance(agent_context, dict):
        agent_context = {}

    service = HostOnboardingService(db)
    try:
        result = await service.accommodation_agent_turn(
            host_id=current_host.id,
            message=transcript,
            focused_item_id=request.focused_item_id,
            checklist_state=[item.model_dump() for item in request.checklist_state],
            accommodation_snapshot={
                **snapshot,
                "_agent_context": {
                    **agent_context,
                    "pending_patch": agent_context.get("pending_patch") or {},
                    "active_item_id": request.focused_item_id,
                    "checklist_state": [item.model_dump() for item in request.checklist_state],
                    "source": "voice_ingest",
                },
            },
            conversation_history=[msg.model_dump() for msg in request.conversation_history],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest voice into accommodation agent",
        ) from exc

    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    result["metadata"] = service._scrub_accommodation_agent_metadata(
        {**metadata, "transcript": transcript, "ingested_via": "voice"}
    )
    result["checklist_updates"] = service._normalize_checklist_updates(
        result.get("checklist_updates") or []
    )
    return AccommodationAgentMessageResponse(**result)
