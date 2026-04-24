"""
Fetch daily trending searches and generate psychology-angle topics from them.
Uses Google Trends RSS (no API key) + Claude for relevance mapping.
"""
import json
import logging
import xml.etree.ElementTree as ET

import requests
import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_PSYCH_KEYWORDS = {
    "stress", "anxiety", "depression", "happiness", "motivation", "fear",
    "habit", "mind", "brain", "emotion", "mental", "behavior", "psychology",
    "social", "relationship", "trust", "confidence", "trauma", "memory",
    "sleep", "addiction", "attention", "focus", "grief", "anger", "regret",
    "envy", "loneliness", "burnout", "narcissism", "empathy", "ego",
}


def _fetch_google_trends(geo: str = "US") -> list[str]:
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        topics = [el.text.strip() for el in root.findall(".//item/title") if el.text]
        return topics[:20]
    except Exception as exc:
        logger.warning("Google Trends RSS failed (%s): %s", geo, exc)
        return []


def _has_psych_angle(topic: str) -> bool:
    words = set(topic.lower().split())
    return bool(words & _PSYCH_KEYWORDS)


def get_fresh_topics(n: int = 5) -> list[str]:
    """
    Return up to n fresh psychology topics derived from today's trending searches.
    Falls back to [] on any error — never blocks the pipeline.
    """
    try:
        trends = _fetch_google_trends("US") or _fetch_google_trends("ID")
        if not trends:
            return []

        # direct psychology matches
        direct = [t for t in trends if _has_psych_angle(t)]
        if len(direct) >= n:
            logger.info("Trending: %d direct psych matches", len(direct))
            return direct[:n]

        # ask Claude to map trending topics → psychology angles
        trend_str = "\n".join(f"- {t}" for t in trends[:10])
        resp = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    f"Today's trending topics:\n{trend_str}\n\n"
                    f"Generate {n} punchy YouTube Shorts psychology topics inspired by "
                    "these trends. Each should be a psychology concept or human behavior "
                    "phenomenon that relates to current events. "
                    f"Return ONLY a JSON array of {n} strings."
                ),
            }],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        topics = json.loads(raw.strip())
        logger.info("Trending: generated %d psychology angles from trends", len(topics))
        return topics[:n]

    except Exception as exc:
        logger.warning("get_fresh_topics failed: %s", exc)
        return []
