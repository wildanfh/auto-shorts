"""
Fetch YouTube video stats (views, likes, comments, avg view duration %)
using the YouTube Data API v3 + YouTube Analytics API.

Called ~24h after upload so numbers are meaningful.
"""
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config.settings import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _creds() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=_SCOPES,
    )
    creds.refresh(Request())
    return creds


def _video_id(url: str) -> str:
    """Extract video ID from youtube.com/shorts/<id> or youtu.be/<id>."""
    for sep in ("/shorts/", "/watch?v=", "youtu.be/"):
        if sep in url:
            return url.split(sep)[-1].split("&")[0].split("?")[0]
    return url.strip("/").split("/")[-1]


def fetch_stats(youtube_url: str) -> dict:
    """
    Return dict with views, likes, comments, avg_view_pct.
    Returns empty dict on any failure — never crashes pipeline.
    """
    if not youtube_url:
        return {}
    try:
        vid_id = _video_id(youtube_url)
        creds  = _creds()

        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        resp = yt.videos().list(
            part="statistics,contentDetails",
            id=vid_id,
        ).execute()

        items = resp.get("items", [])
        if not items:
            logger.warning("Analytics: no data for video %s", vid_id)
            return {}

        stats = items[0]["statistics"]
        views    = int(stats.get("viewCount", 0))
        likes    = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        # avg view duration % via YouTube Analytics API
        avg_pct = ""
        try:
            ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
            ar = ya.reports().query(
                ids=f"channel==MINE",
                startDate="2020-01-01",
                endDate="2099-12-31",
                metrics="averageViewPercentage",
                filters=f"video=={vid_id}",
                dimensions="video",
            ).execute()
            rows = ar.get("rows", [])
            if rows:
                avg_pct = f"{rows[0][1]:.1f}%"
        except Exception as exc:
            logger.debug("Analytics API avg view pct failed: %s", exc)

        result = {
            "views": views,
            "likes": likes,
            "comments": comments,
            "avg_view_pct": avg_pct,
            "like_ratio": f"{likes/views*100:.2f}%" if views else "0%",
        }
        logger.info("Analytics fetched for %s: %s", vid_id, result)
        return result

    except Exception as exc:
        logger.warning("fetch_stats failed for %s: %s", youtube_url, exc)
        return {}
