"""Voice bridge for the Stay-tab accommodation onboarding agent."""

import asyncio
import base64
import json
import os
import struct
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
try:  # websocket transport errors differ by installed optional packages.
    from websockets.exceptions import ConnectionClosed
except Exception:  # pragma: no cover - depends on local optional dependency set
    class ConnectionClosed(Exception):
        pass

from app.db.postgresql.connection import AsyncSessionLocal
from app.services.host_service import HostService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/onboarding/accommodation/voice", tags=["accommodation-voice"])

GEMINI_INPUT_RATE = 16000
DEFAULT_VOICE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_VOICE_NAME = "Zephyr"


def _resample_pcm_to_16k(pcm_bytes: bytes, from_rate: int) -> bytes:
    """Resample 16-bit LE mono PCM from from_rate to 16kHz."""
    if from_rate == GEMINI_INPUT_RATE or not pcm_bytes:
        return pcm_bytes
    n_in = len(pcm_bytes) // 2
    n_out = int(n_in * GEMINI_INPUT_RATE / from_rate)
    if n_out <= 0:
        return b""
    out = bytearray(n_out * 2)
    for i in range(n_out):
        pos = i * from_rate / GEMINI_INPUT_RATE
        idx = int(pos)
        frac = pos - idx
        if idx >= n_in - 1:
            sample = struct.unpack_from("<h", pcm_bytes, (n_in - 1) * 2)[0]
        else:
            a = struct.unpack_from("<h", pcm_bytes, idx * 2)[0]
            b = struct.unpack_from("<h", pcm_bytes, (idx + 1) * 2)[0]
            sample = max(-32768, min(32767, int(a + (b - a) * frac)))
        struct.pack_into("<h", out, i * 2, sample)
    return bytes(out)


def _looks_like_base64_ascii(data: bytes) -> bool:
    if not data or len(data) % 4 != 0:
        return False
    allowed = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n"
    return all(ch in allowed for ch in data)


def _normalize_live_audio_bytes(raw_data) -> bytes:
    if not raw_data:
        return b""
    raw = bytes(raw_data) if not isinstance(raw_data, bytes) else raw_data
    if isinstance(raw_data, str) or _looks_like_base64_ascii(raw):
        raw = base64.b64decode(raw_data if isinstance(raw_data, str) else raw)
    return raw


async def _authenticate_voice_session(token: Optional[str]):
    if not token:
        return None, None, "Session token required"
    async with AsyncSessionLocal() as db:
        host = await HostService(db).get_current_host_from_session(token)
        if not host:
            return None, None, "Invalid session token"
        settings_service = SettingsService(db)
        host_settings = await settings_service.get_host_settings(host.id)
        if host_settings and not host_settings.enable_voice_interface:
            return None, None, "Voice interface is disabled for this host"
        api_key = await settings_service.get_host_api_key(str(host.id), "google_ai")
        api_key = api_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        snapshot = {
            "host_id": str(host.id),
            "name": f"{host.first_name} {host.last_name}".strip(),
            "city": host.city,
            "county": host.county,
            "business_name": host.business_name,
            "business_type": host.business_type,
            "description": host.description,
            "languages": host.languages or ["hr", "en"],
        }
        return host, {"api_key": api_key, "snapshot": snapshot}, None


@router.get("/health")
async def accommodation_voice_health():
    return {"status": "ok", "service": "accommodation-voice"}


@router.websocket("/stream")
async def accommodation_voice_stream(websocket: WebSocket):
    await websocket.accept()
    token = websocket.query_params.get("token")
    _host, auth_context, auth_error = await _authenticate_voice_session(token)
    if auth_error:
        await websocket.close(code=1008, reason=auth_error)
        return
    if not auth_context or not auth_context.get("api_key"):
        await websocket.close(code=1008, reason="Google AI key missing")
        return

    try:
        from google import genai
        from google.genai import types
    except Exception:
        await websocket.close(code=1011, reason="google-genai SDK is not installed")
        return

    async def send_audio_chunk(session, pcm_bytes: bytes):
        audio_blob = types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
        if hasattr(session, "send_realtime_input"):
            await session.send_realtime_input(audio=audio_blob)
        else:
            await session.send(input={"data": pcm_bytes, "mime_type": "audio/pcm;rate=16000"})

    async def send_text_turn(session, text: str):
        if hasattr(session, "send"):
            await session.send(input=text, end_of_turn=True)
        else:
            await session.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text=text)]),
                turn_complete=True,
            )

    try:
        client = genai.Client(api_key=auth_context["api_key"], http_options={"api_version": "v1beta"})
        voice_name = os.environ.get("GEMINI_VOICE_NAME", DEFAULT_VOICE_NAME)
        model_id = os.environ.get("GEMINI_VOICE_MODEL", DEFAULT_VOICE_MODEL)
        system_instruction = f"""
You are the HostForGuest voice onboarding agent for the Stay tab.
Talk naturally and briefly. Ask one focused question at a time to collect property facts:
name, type, capacity, exact location, GPS, story, amenities, services, specialties,
languages, welcome message, photos, and rules.
Never claim that a profile change is saved. Tell the host that drafts must be reviewed and saved on screen.
Host snapshot: {auth_context["snapshot"]}
"""
        config = types.LiveConnectConfig(
            responseModalities=["AUDIO"],
            temperature=0.35,
            speechConfig=types.SpeechConfig(
                voiceConfig=types.VoiceConfig(
                    prebuiltVoiceConfig=types.PrebuiltVoiceConfig(voiceName=voice_name)
                )
            ),
            inputAudioTranscription=types.AudioTranscriptionConfig(),
            outputAudioTranscription=types.AudioTranscriptionConfig(),
            systemInstruction=types.Content(parts=[types.Part(text=system_instruction)]),
            realtimeInputConfig=types.RealtimeInputConfig(
                automaticActivityDetection=types.AutomaticActivityDetection(
                    disabled=False,
                    startOfSpeechSensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    endOfSpeechSensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefixPaddingMs=80,
                    silenceDurationMs=500,
                ),
                activityHandling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                turnCoverage=types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
            ),
        )

        async with client.aio.live.connect(model=model_id, config=config) as session:
            await websocket.send_text(json.dumps({"type": "session_ready"}))

            async def frontend_to_gemini():
                try:
                    while True:
                        msg = json.loads(await websocket.receive_text())
                        if msg.get("type") == "audio_chunk" and msg.get("data"):
                            pcm = base64.b64decode(msg["data"])
                            sample_rate = int(msg.get("sample_rate") or GEMINI_INPUT_RATE)
                            if sample_rate != GEMINI_INPUT_RATE:
                                pcm = _resample_pcm_to_16k(pcm, sample_rate)
                            await send_audio_chunk(session, pcm)
                        elif msg.get("type") == "text_turn" and (msg.get("text") or "").strip():
                            await send_text_turn(session, msg["text"].strip())
                except (WebSocketDisconnect, asyncio.CancelledError, ConnectionClosed):
                    return

            async def gemini_to_frontend():
                try:
                    while True:
                        async for response in session.receive():
                            server_content = getattr(response, "server_content", None)
                            raw_data = getattr(response, "data", None)
                            if raw_data:
                                raw = _normalize_live_audio_bytes(raw_data)
                                if raw:
                                    await websocket.send_text(json.dumps({
                                        "type": "audio_chunk",
                                        "data": base64.b64encode(raw).decode("utf-8"),
                                        "mime_type": "audio/pcm;rate=24000",
                                    }))
                            if server_content is not None:
                                if getattr(server_content, "interrupted", False):
                                    await websocket.send_text(json.dumps({"type": "interrupted"}))
                                if getattr(server_content, "turn_complete", False):
                                    await websocket.send_text(json.dumps({"type": "turn_complete"}))
                                    break
                except (WebSocketDisconnect, asyncio.CancelledError, ConnectionClosed):
                    return

            done, pending = await asyncio.wait(
                {asyncio.create_task(frontend_to_gemini()), asyncio.create_task(gemini_to_frontend())},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    raise exc
    except Exception as e:
        try:
            await websocket.close(code=1011, reason=f"Gemini voice error: {str(e)}")
        except Exception:
            pass
