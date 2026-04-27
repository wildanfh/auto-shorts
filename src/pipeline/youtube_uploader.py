import json
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config.settings import (
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_PRIVACY,
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_TAGS,
)

logger = logging.getLogger(__name__)

_TOKEN_URI    = "https://oauth2.googleapis.com/token"
_COUNTER_FILE = Path(__file__).parent.parent.parent / "data" / "series_counter.json"


def _next_episode() -> int:
    """Read, increment, persist, and return the next episode number."""
    n = json.loads(_COUNTER_FILE.read_text())["n"] if _COUNTER_FILE.exists() else 0
    n += 1
    _COUNTER_FILE.write_text(json.dumps({"n": n}))
    return n
_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _build_client():
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri=_TOKEN_URI,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=_SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


_HOOK_TEMPLATES = [
    "Why {topic} 🧠",
    "The truth about {topic}",
    "Nobody tells you this about {topic}",
    "Your brain is lying to you about {topic}",
    "This is why {topic} — psychology explained",
    "{topic}: the science is wild",
]


def _make_title(topic: str, ep: int) -> str:
    import hashlib
    idx = int(hashlib.md5(topic.encode()).hexdigest()[:2], 16) % len(_HOOK_TEMPLATES)
    raw = _HOOK_TEMPLATES[idx].format(topic=topic)
    return raw[:100]


def upload_video(video_path: Path, topic: str, script: str) -> str:
    """Upload MP4 to YouTube Shorts, return the video URL."""
    youtube = _build_client()

    ep    = _next_episode()
    title = _make_title(topic, ep)
    # First sentence of script as description hook, then hashtags
    first_sentence = script.split(".")[0].strip() if "." in script else script[:120].strip()
    description = (
        f"{first_sentence}.\n\n"
        "#Shorts #psychology #mindset #psychologyfacts #brain "
        "#selfimprovement #mentalhealth #learnontiktok #science #facts"
    )

    topic_tags = [w.lower() for w in topic.split() if len(w) > 3][:3]
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": YOUTUBE_TAGS + topic_tags,
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,  # 1 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.debug("Upload progress: %d%%", int(status.progress() * 100))

    video_id = response["id"]
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    logger.info("Uploaded: %s", video_url)
    return video_url
