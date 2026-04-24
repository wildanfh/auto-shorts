"""
Entry point.

Run on schedule:   python main.py
Run immediately:   python main.py --now
"""

import argparse
import json
import logging
import time
from pathlib import Path

import schedule

from src.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

# 8 AM, 2 PM, 8 PM — system local time
_SCHEDULE_TIMES = ["08:00", "14:00", "20:00"]


_PENDING_FILE = Path(__file__).parent / "data" / "analytics_pending.json"


def _safe_run() -> None:
    try:
        run_pipeline()
    except Exception:
        pass  # runner already logs; keep scheduler alive


def _fetch_pending_analytics() -> None:
    """Check for runs that are ~24h old and haven't had analytics fetched yet."""
    if not _PENDING_FILE.exists():
        return
    try:
        from src.utils.analytics_fetcher import fetch_stats
        from src.pipeline.sheets_logger import update_analytics

        pending = json.loads(_PENDING_FILE.read_text())
        still_pending = []
        now = time.time()

        for entry in pending:
            age_h = (now - entry["ts"]) / 3600
            if age_h < 23:
                still_pending.append(entry)
                continue
            stats = fetch_stats(entry["url"])
            update_analytics(entry["run_id"], stats)
            logger.info("Analytics updated for run_id=%s", entry["run_id"])

        _PENDING_FILE.write_text(json.dumps(still_pending))
    except Exception as exc:
        logger.warning("Analytics fetch failed: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="Run one pipeline immediately")
    args = parser.parse_args()

    if args.now:
        run_pipeline()
        return

    for t in _SCHEDULE_TIMES:
        schedule.every().day.at(t).do(_safe_run)

    # check analytics every hour (runs are eligible after 23h)
    schedule.every().hour.do(_fetch_pending_analytics)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
    logger.info("Scheduler started. Jobs: %s", _SCHEDULE_TIMES)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
