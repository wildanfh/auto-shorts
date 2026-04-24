import json
import logging
import random

from config.settings import TOPICS_FILE, USED_TOPICS_FILE

logger = logging.getLogger(__name__)


def pick_topic() -> str:
    """Return an unused psychology topic, cycling back when all are exhausted."""
    topics: list[str] = json.loads(TOPICS_FILE.read_text())
    used: list[str]   = json.loads(USED_TOPICS_FILE.read_text())

    available = [t for t in topics if t not in used]

    if not available:
        logger.info("All topics used — resetting pool")
        used = []
        available = topics[:]

    topic = random.choice(available)
    used.append(topic)
    USED_TOPICS_FILE.write_text(json.dumps(used, indent=2))
    logger.info("Topic picked: %s", topic)
    return topic
