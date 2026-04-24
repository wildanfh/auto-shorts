import base64
import logging
import time
from pathlib import Path

import requests

from config.settings import (
    CREATOMATE_API_KEY,
    CREATOMATE_TEMPLATE_ID,
    OUTPUT_VIDEO_DIR,
)
from src.utils.script_parser import extract_captions

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.creatomate.com/v1"
_HEADERS = {"Authorization": f"Bearer {CREATOMATE_API_KEY}"}
_POLL_INTERVAL = 5   # seconds between status checks
_POLL_TIMEOUT = 300  # give up after 5 minutes


def _audio_to_data_url(audio_path: Path) -> str:
    """Encode local MP3 as a base64 data URL for inline Creatomate delivery."""
    data = base64.b64encode(audio_path.read_bytes()).decode()
    return f"data:audio/mpeg;base64,{data}"


def _create_render(audio_url: str, topic: str, script: str) -> str:
    """Submit render job, return render ID."""
    captions = extract_captions(script, max_lines=5)

    modifications: dict = {"Audio-1": audio_url, "Text-1": topic}
    for i, line in enumerate(captions, start=2):
        modifications[f"Text-{i}"] = line

    payload = {
        "template_id": CREATOMATE_TEMPLATE_ID,
        "modifications": modifications,
    }
    resp = requests.post(
        f"{_BASE_URL}/renders",
        headers={**_HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    renders = resp.json()
    render_id = renders[0]["id"]
    logger.info("Render created: %s", render_id)
    return render_id


def _poll_render(render_id: str) -> str:
    """Block until render succeeds, return download URL."""
    deadline = time.time() + _POLL_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{_BASE_URL}/renders/{render_id}",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data["status"]

        if status == "succeeded":
            return data["url"]
        if status == "failed":
            raise RuntimeError(f"Render {render_id} failed: {data.get('error')}")

        logger.debug("Render status: %s — waiting %ds", status, _POLL_INTERVAL)
        time.sleep(_POLL_INTERVAL)

    raise TimeoutError(f"Render {render_id} not done after {_POLL_TIMEOUT}s")


def _download_video(url: str, run_id: str) -> Path:
    """Download rendered MP4 to output/video/."""
    OUTPUT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_VIDEO_DIR / f"video_{run_id}.mp4"

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Video downloaded: %s (%.1f MB)", out_path, size_mb)
    return out_path


def render_video(audio_path: Path, topic: str, run_id: str, script: str = "") -> Path:
    """Full Creatomate render flow: encode audio → render → download MP4."""
    audio_url = _audio_to_data_url(audio_path)
    render_id = _create_render(audio_url, topic, script)
    video_url = _poll_render(render_id)
    return _download_video(video_url, run_id)
