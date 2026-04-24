"""
Kling AI text-to-video client.

Flow: generate JWT → submit tasks in parallel → poll until all done → download MP4s.
"""
import logging
import time
from pathlib import Path

import jwt
import requests

from config.settings import KLING_AI_ACCESS_KEY, KLING_AI_SECRET_KEY

logger = logging.getLogger(__name__)

_BASE      = "https://api.klingai.com"
_MODEL     = "kling-v1"
_MODE      = "std"          # "std" or "pro"
_DURATION  = "5"            # "5" or "10" seconds per clip
_RATIO     = "9:16"
_CFG       = 0.5
_POLL_INT  = 10             # seconds between polls
_TIMEOUT   = 600            # give up after 10 min per clip
_SUBMIT_DELAY  = 4          # seconds between submissions to avoid 429
_MAX_CLIPS     = 4          # cap Kling to 4 clips; Pexels fills the rest
_RETRY_WAITS   = (30, 60, 120)  # backoff on 429


def _token() -> str:
    """Generate short-lived HS256 JWT for Kling API."""
    now = int(time.time())
    payload = {"iss": KLING_AI_ACCESS_KEY, "exp": now + 1800, "nbf": now - 5}
    return jwt.encode(payload, KLING_AI_SECRET_KEY, algorithm="HS256",
                      headers={"alg": "HS256", "typ": "JWT"})


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _submit(prompt: str) -> str:
    """Submit one text2video task; retries on 429 with exponential backoff."""
    last_exc = None
    for attempt, wait in enumerate([0] + list(_RETRY_WAITS)):
        if wait:
            logger.info("Kling 429 — retry %d in %ds…", attempt, wait)
            time.sleep(wait)
        try:
            resp = requests.post(
                f"{_BASE}/v1/videos/text2video",
                headers=_headers(),
                json={
                    "model_name":      _MODEL,
                    "prompt":          prompt,
                    "negative_prompt": "text, watermark, blurry, low quality, logo",
                    "cfg_scale":       _CFG,
                    "mode":            _MODE,
                    "duration":        _DURATION,
                    "aspect_ratio":    _RATIO,
                },
                timeout=30,
            )
            if resp.status_code == 429:
                last_exc = requests.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            body = resp.json()
            if body.get("code", 0) != 0:
                raise RuntimeError(f"Kling submit error: {body}")
            task_id = body["data"]["task_id"]
            logger.debug("Kling task submitted: %s", task_id)
            return task_id
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                last_exc = exc
                continue
            raise
    raise RuntimeError(f"Kling 429 after all retries") from last_exc


def _poll_one(task_id: str) -> str:
    """Block until task succeeds, return video URL."""
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{_BASE}/v1/videos/text2video/{task_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("task_status", "")

        if status == "succeed":
            videos = data.get("task_result", {}).get("videos", [])
            if videos:
                return videos[0]["url"]
            raise RuntimeError(f"Task {task_id} succeeded but no video URL")
        if status == "failed":
            raise RuntimeError(f"Kling task {task_id} failed: {data.get('task_status_msg')}")

        logger.debug("Kling %s → %s, waiting %ds…", task_id, status, _POLL_INT)
        time.sleep(_POLL_INT)

    raise TimeoutError(f"Kling task {task_id} not done after {_TIMEOUT}s")


def _download(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(path, "wb") as fp:
            for chunk in r.iter_content(8192):
                fp.write(chunk)


def generate_clips(prompts: list[str], run_id: str) -> list[Path]:
    """
    Submit all prompts, poll until done, download MP4s.
    Returns list of local paths (skips any that failed).
    """
    if not (KLING_AI_ACCESS_KEY and KLING_AI_SECRET_KEY):
        logger.warning("Kling keys not configured")
        return []

    # cap batch size — stay within free-tier rate limits
    batch = prompts[:_MAX_CLIPS]

    task_ids: list[tuple[int, str]] = []
    for i, prompt in enumerate(batch):
        try:
            tid = _submit(prompt)
            task_ids.append((i, tid))
            logger.info("Kling submitted clip %d/%d", i + 1, len(batch))
        except Exception as exc:
            logger.warning("Kling submit failed (clip %d): %s", i, exc)
        if i < len(batch) - 1:
            time.sleep(_SUBMIT_DELAY)

    # poll + download
    paths: list[Path] = []
    for i, tid in task_ids:
        try:
            url  = _poll_one(tid)
            path = Path(f"/tmp/kling_{run_id}_{i}.mp4")
            _download(url, path)
            paths.append(path)
            logger.info("Kling clip %d downloaded: %s", i, path)
        except Exception as exc:
            logger.warning("Kling clip %d failed: %s", i, exc)

    logger.info("Kling: %d/%d clips ready", len(paths), len(prompts))
    return paths
