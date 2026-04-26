import json
import logging
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from config.settings import OPENAI_API_KEY, OUTPUT_AUDIO_DIR

logger = logging.getLogger(__name__)

_VOICE     = "onyx"
_TTS_MODEL = "tts-1"


def generate_voiceover(script: str, run_id: str | None = None) -> Path:
    client = OpenAI(api_key=OPENAI_API_KEY)

    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    stamp    = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    mp3_path = OUTPUT_AUDIO_DIR / f"voiceover_{stamp}.mp3"
    json_path = mp3_path.with_suffix(".json")

    # Generate TTS
    response = client.audio.speech.create(
        model=_TTS_MODEL,
        voice=_VOICE,
        input=script,
        speed=1.1,
    )
    response.stream_to_file(mp3_path)

    # Word-level timestamps via Whisper
    with open(mp3_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )

    words = getattr(transcript, "words", []) or []
    json_path.write_text(json.dumps({
        "words": [{"word": w.word, "start": w.start, "end": w.end} for w in words]
    }))

    size_kb = mp3_path.stat().st_size // 1024
    logger.info("Voiceover saved: %s (%d KB) — words: %d", mp3_path, size_kb, len(words))
    return mp3_path
