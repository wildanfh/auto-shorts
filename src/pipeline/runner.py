import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.topic_picker import pick_topic
from src.pipeline.script_generator import generate_script
from src.pipeline.voiceover import generate_voiceover
from src.pipeline.video_creator import create_video
from src.pipeline.youtube_uploader import upload_video
from src.pipeline.sheets_logger import log_run
from src.utils.logger import setup_logging
from src.utils.telegram import send_summary
from config.settings import LOGS_DIR

logger = logging.getLogger(__name__)


_PENDING_FILE = Path(__file__).parent.parent.parent / "data" / "analytics_pending.json"


def _queue_analytics(run_id: str, youtube_url: str) -> None:
    try:
        pending = json.loads(_PENDING_FILE.read_text()) if _PENDING_FILE.exists() else []
        pending.append({"run_id": run_id, "url": youtube_url, "ts": time.time()})
        _PENDING_FILE.write_text(json.dumps(pending))
    except Exception as exc:
        logger.warning("Failed to queue analytics: %s", exc)


def run_pipeline() -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    setup_logging(run_id)
    logger.info("=== Pipeline start  run_id=%s ===", run_id)

    topic = script = None
    audio_path = video_path = None
    youtube_url = ""

    try:
        topic = pick_topic()

        script = generate_script(topic)

        audio_path = generate_voiceover(script, run_id=run_id)

        video_path = create_video(audio_path, topic, script=script, run_id=run_id)

        youtube_url = upload_video(video_path, topic, script)

        log_run(
            run_id=run_id,
            topic=topic,
            script=script,
            audio_path=audio_path,
            video_path=video_path,
            youtube_url=youtube_url,
        )

        # queue analytics fetch for ~24h later
        _queue_analytics(run_id, youtube_url)

        logger.info("=== Pipeline complete  url=%s ===", youtube_url)
        send_summary(
            run_id=run_id,
            topic=topic,
            youtube_url=youtube_url,
            status="success",
            log_path=LOGS_DIR / f"run_{run_id}.log",
        )

    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        log_run(
            run_id=run_id,
            topic=topic or "",
            script=script or "",
            audio_path=audio_path,
            video_path=video_path,
            youtube_url=youtube_url,
            status="error",
            error=str(exc),
        )
        send_summary(
            run_id=run_id,
            topic=topic or "",
            youtube_url=youtube_url,
            status="error",
            error=str(exc),
            log_path=LOGS_DIR / f"run_{run_id}.log",
        )
        raise
