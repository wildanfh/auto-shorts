import logging
from pathlib import Path

import requests

from config.settings import FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN

logger = logging.getLogger(__name__)

_GRAPH = "https://graph-video.facebook.com/v25.0"


def upload_reel(video_path: Path, topic: str, script: str) -> str:
    """Upload MP4 as a Facebook Reel via 3-step resumable upload.

    /video_reels endpoint gives organic Reel reach vs /videos (page video, near-zero reach).
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.warning("Facebook credentials not set — skipping FB upload")
        return ""

    description = (
        f"{topic}\n\n"
        "#psychology #shorts #mindset #science #psychologyfacts "
        "#brain #selfimprovement #mentalhealth #facts"
    )
    token     = FACEBOOK_PAGE_ACCESS_TOKEN
    page_id   = FACEBOOK_PAGE_ID
    file_size = video_path.stat().st_size

    # Step 1: initialize upload
    init = requests.post(
        f"{_GRAPH}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": token},
        timeout=30,
    )
    init.raise_for_status()
    data       = init.json()
    video_id   = data["video_id"]
    upload_url = data["upload_url"]

    # Step 2: upload bytes
    with open(video_path, "rb") as fp:
        up = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(file_size),
            },
            data=fp,
            timeout=300,
        )
    up.raise_for_status()

    # Step 3: publish
    pub = requests.post(
        f"{_GRAPH}/{page_id}/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "access_token": token,
        },
        timeout=30,
    )
    pub.raise_for_status()

    url = f"https://www.facebook.com/reel/{video_id}"
    logger.info("Facebook Reel uploaded: %s", url)
    return url
