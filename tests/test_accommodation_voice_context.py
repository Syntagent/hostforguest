"""Voice must ingest through the accommodation agent, not a separate chat persona."""

import base64
import struct

from app.api.v1 import accommodation_voice


def test_pcm_to_wav_wraps_audio():
    pcm = struct.pack("<h", 0) * 800
    wav = accommodation_voice._pcm_to_wav(pcm, 16000)
    assert wav[:4] == b"RIFF"
    assert b"WAVE" in wav[:16]


def test_merge_snapshot_prefers_client_values():
    db = {"property_name": "Old", "city": "Lovran"}
    client = {"property_name": "Villa Oprić 71", "location_story": "Nature and sea."}
    merged = accommodation_voice._merge_snapshot(db, client)
    assert merged["property_name"] == "Villa Oprić 71"
    assert merged["location_story"] == "Nature and sea."


def test_voice_ingest_request_allows_audio_without_message():
    from app.api.v1.accommodation_voice import VoiceIngestRequest

    req = VoiceIngestRequest(
        audio_base64=base64.b64encode(b"\x00\x00" * 4000).decode(),
        focused_item_id="location_story",
    )
    assert req.message is None
    assert req.audio_base64
