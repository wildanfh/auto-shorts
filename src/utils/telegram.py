import logging
from pathlib import Path

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/{method}"


def _send(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured — skipping notification")
        return

    resp = requests.post(
        _API.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage"),
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("Telegram notification sent")


def send_summary(
    *,
    run_id: str,
    topic: str,
    youtube_url: str,
    status: str,
    error: str = "",
    log_path: Path | None = None,
) -> None:
    try:
        if status == "success":
            text = (
                f"✅ <b>Short published!</b>\n"
                f"🎯 <b>Topic:</b> {topic}\n"
                f"▶️ <b>URL:</b> {youtube_url}\n"
                f"🆔 <code>{run_id}</code>"
            )
        else:
            tail = ""
            if log_path and log_path.exists():
                last_lines = log_path.read_text().splitlines()[-15:]
                tail = "\n<pre>" + "\n".join(last_lines) + "</pre>"

            text = (
                f"❌ <b>Pipeline failed</b>\n"
                f"🎯 <b>Topic:</b> {topic or 'N/A'}\n"
                f"💥 <b>Error:</b> <code>{error[:300]}</code>\n"
                f"🆔 <code>{run_id}</code>"
                f"{tail}"
            )

        _send(text)
    except Exception as exc:
        # Notification failure must never crash the pipeline
        logger.error("Telegram notify failed: %s", exc)
