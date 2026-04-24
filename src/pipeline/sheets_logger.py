import logging
from datetime import datetime, timezone
from pathlib import Path

import json

import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from config.settings import GOOGLE_SHEET_ID

logger = logging.getLogger(__name__)

_TOKEN_FILE = Path(__file__).parent.parent.parent / "config" / "sheets_token.json"
_HEADER = [
    "run_id", "timestamp_utc", "topic",
    "script", "audio_path", "video_path",
    "youtube_url", "status", "error",
    "views_24h", "likes_24h", "comments_24h", "avg_view_pct", "like_ratio",
]


def _get_sheet():
    if not _TOKEN_FILE.exists():
        raise FileNotFoundError(
            "config/sheets_token.json not found. Run: python get_sheets_token.py"
        )

    data = json.loads(_TOKEN_FILE.read_text())
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )

    if creds.expired:
        creds.refresh(Request())
        # persist refreshed token
        data["token"] = creds.token
        _TOKEN_FILE.write_text(json.dumps(data))

    gc = gspread.authorize(creds)
    ws = gc.open_by_key(GOOGLE_SHEET_ID).sheet1

    if not ws.row_values(1):
        ws.append_row(_HEADER)

    return ws


def log_run(
    *,
    run_id: str,
    topic: str,
    script: str,
    audio_path: Path | None = None,
    video_path: Path | None = None,
    youtube_url: str = "",
    status: str = "success",
    error: str = "",
) -> None:
    """Append one row to the Google Sheet for this pipeline run."""
    try:
        ws = _get_sheet()
        row = [
            run_id,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            topic,
            script[:500],  # cap to avoid cell limit issues
            str(audio_path) if audio_path else "",
            str(video_path) if video_path else "",
            youtube_url,
            status,
            error[:200] if error else "",
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Logged to Sheets: run_id=%s status=%s", run_id, status)
    except Exception as exc:
        logger.error("Sheets log failed: %s", exc)


def update_analytics(run_id: str, stats: dict) -> None:
    """
    Find the row matching run_id and fill in analytics columns.
    Called ~24h after upload.
    """
    if not stats:
        return
    try:
        ws   = _get_sheet()
        ids  = ws.col_values(1)            # column A = run_id
        try:
            row_num = ids.index(run_id) + 1
        except ValueError:
            logger.warning("update_analytics: run_id %s not found in sheet", run_id)
            return

        headers = ws.row_values(1)
        col_map = {h: i + 1 for i, h in enumerate(headers)}

        for key in ("views_24h", "likes_24h", "comments_24h", "avg_view_pct", "like_ratio"):
            api_key = key.replace("_24h", "").replace("views", "views").replace("likes", "likes").replace("comments", "comments")
            value   = stats.get(api_key, stats.get(key, ""))
            if key in col_map and value != "":
                ws.update_cell(row_num, col_map[key], str(value))

        logger.info("Analytics updated in Sheets for run_id=%s", run_id)
    except Exception as exc:
        logger.error("update_analytics failed: %s", exc)
