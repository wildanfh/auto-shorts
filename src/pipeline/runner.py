import logging
from datetime import datetime, timezone

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
