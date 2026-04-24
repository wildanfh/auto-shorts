"""
Entry point.

Run on schedule:   python main.py
Run immediately:   python main.py --now
"""

import argparse
import logging
import time

import schedule

from src.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

# 8 AM, 2 PM, 8 PM — system local time
_SCHEDULE_TIMES = ["08:00", "14:00", "20:00"]


def _safe_run() -> None:
    try:
        run_pipeline()
    except Exception:
        pass  # runner already logs; keep scheduler alive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="Run one pipeline immediately")
    args = parser.parse_args()

    if args.now:
        run_pipeline()
        return

    for t in _SCHEDULE_TIMES:
        schedule.every().day.at(t).do(_safe_run)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
    logger.info("Scheduler started. Jobs: %s", _SCHEDULE_TIMES)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
