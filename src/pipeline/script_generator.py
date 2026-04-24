import logging

import anthropic

from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    SCRIPT_MAX_TOKENS,
    SCRIPT_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_script(topic: str) -> str:
    """Generate a 60-second YouTube Shorts script for the given psychology topic."""
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=SCRIPT_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": SCRIPT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Write a 60-second YouTube Shorts script about: {topic}",
            }
        ],
    )

    script = response.content[0].text.strip()
    word_count = len(script.split())
    logger.info("Script generated: %d words (topic: %s)", word_count, topic)
    return script
