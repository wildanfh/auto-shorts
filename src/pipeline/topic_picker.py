import json
import logging
import random

from config.settings import TOPICS_FILE, USED_TOPICS_FILE

logger = logging.getLogger(__name__)

# ICP keywords for psychology Shorts channel (derived from analytics winners).
# Personal/relatable framing outperforms abstract academic terms.
_HIGH_VALUE = [
    "you", "your", "why", "feel", "feeling", "brain", "mind", "people",
    "emotion", "emotional", "relationship", "habit", "behavior", "social",
    "anxiety", "stress", "confidence", "happy", "happiness", "fear",
    "love", "friend", "family", "work", "money", "success", "fail",
    "psychology", "science", "research", "study", "effect", "bias",
]
# Academic jargon that performs worse on Shorts (harder hook, less relatable)
_JARGON_PENALTY = [
    "dunning-kruger", "mere exposure", "zeigarnik", "reactance",
    "priming", "heuristic", "attribution", "operant", "classical",
    "cognitive dissonance",
]
# Second-person framing = strong Shorts hook signal
_SECOND_PERSON = ["you ", "your ", "why you", "how you", "when you"]


def _score(topic: str) -> float:
    t = topic.lower()
    score = 0.0
    for kw in _HIGH_VALUE:
        if kw in t:
            score += 1.0
    for kw in _JARGON_PENALTY:
        if kw in t:
            score -= 2.0
    for kw in _SECOND_PERSON:
        if kw in t:
            score += 1.5   # extra weight for "you/your" framing
    return score


def pick_topic() -> str:
    """Return an unused psychology topic, scored by ICP relevance.

    Picks randomly among the top-3 scoring available topics to maintain
    variety while biasing toward relatable, second-person framing.
    """
    topics: list[str] = json.loads(TOPICS_FILE.read_text())
    used: list[str]   = json.loads(USED_TOPICS_FILE.read_text())

    available = [t for t in topics if t not in used]

    if not available:
        logger.info("All topics used — resetting pool")
        used = []
        available = topics[:]

    scored = sorted(available, key=_score, reverse=True)
    candidates = scored[:3]
    topic = random.choice(candidates)

    used.append(topic)
    USED_TOPICS_FILE.write_text(json.dumps(used, indent=2))
    logger.info("Topic picked: %s (score=%.1f)", topic, _score(topic))
    return topic
