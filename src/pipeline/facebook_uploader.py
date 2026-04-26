import logging
from pathlib import Path

import requests

from config.settings import FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN

logger = logging.getLogger(__name__)

_GRAPH_VIDEO = "https://graph-video.facebook.com/v25.0"


def upload_reel(video_path: Path, topic: str, script: str) -> str:
    """Upload MP4 to Facebook Page. Short videos appear as Reels in the feed."""
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.warning("Facebook credentials not set — skipping FB upload")
        return ""

    description = f"{topic}\n\n#psychology #shorts #mindset #science #facts"

    with open(video_path, "rb") as fp:
        r = requests.post(
            f"{_GRAPH_VIDEO}/{FACEBOOK_PAGE_ID}/videos",
            data={
                "description":  description,
                "published":    "true",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            },
            files={"source": (video_path.name, fp, "video/mp4")},
            timeout=300,
        )

    r.raise_for_status()
    video_id = r.json().get("id", "")
    url = f"https://www.facebook.com/watch/?v={video_id}"
    logger.info("Facebook video uploaded: %s", url)
    return url
