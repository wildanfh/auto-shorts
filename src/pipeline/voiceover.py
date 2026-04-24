import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from config.settings import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OUTPUT_AUDIO_DIR

logger = logging.getLogger(__name__)

ADAM_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

_VOICE_SETTINGS = VoiceSettings(
    stability=0.50,
    similarity_boost=0.75,
    style=0.00,
    use_speaker_boost=True,
    speed=1.1,
)


def generate_voiceover(script: str, run_id: str | None = None) -> Path:
    """
    Call ElevenLabs with-timestamps TTS.
    Saves MP3 + JSON sidecar (<same stem>.json) with character-level timing.
    Returns path to MP3.
    """
    voice_id = ELEVENLABS_VOICE_ID or ADAM_VOICE_ID
    client   = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    resp = client.text_to_speech.convert_with_timestamps(
        voice_id=voice_id,
        text=script,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
        voice_settings=_VOICE_SETTINGS,
    )

    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    stamp    = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    mp3_path = OUTPUT_AUDIO_DIR / f"voiceover_{stamp}.mp3"
    json_path = mp3_path.with_suffix(".json")

    # save audio
    mp3_path.write_bytes(base64.b64decode(resp.audio_base_64))

    # save alignment sidecar for caption sync
    alignment = resp.alignment
    if alignment:
        json_path.write_text(json.dumps({
            "characters":                   alignment.characters,
            "character_start_times_seconds": alignment.character_start_times_seconds,
            "character_end_times_seconds":   alignment.character_end_times_seconds,
        }))

    size_kb = mp3_path.stat().st_size // 1024
    logger.info("Voiceover saved: %s (%d KB) — alignment: %s",
                mp3_path, size_kb, "yes" if alignment else "no")
    return mp3_path
