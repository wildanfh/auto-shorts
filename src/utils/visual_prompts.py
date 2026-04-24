"""
Generate cinematic Kling AI video prompts from a psychology topic + script.
Uses Claude so prompts are specifically matched to the content.
"""
import json
import logging

import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM = (
    "You generate short cinematic video prompts for Kling AI text-to-video. "
    "Output ONLY a valid JSON array of strings, no explanation."
)


def generate_visual_prompts(topic: str, n: int = 12) -> list[str]:
    """
    Return n cinematic video prompts for Kling AI based on the psychology topic.
    Each prompt is a visual scene, 9:16 vertical, ~5 seconds.
    """
    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Psychology topic: \"{topic}\"\n\n"
                f"Generate {n} short cinematic video prompts for this topic. Rules:\n"
                "- Each prompt: 1-2 sentences, pure visual description\n"
                "- 9:16 vertical format, no text or captions in frame\n"
                "- Varied shots: close-up face, wide environment, abstract, hands, nature\n"
                "- Cinematic, moody, high quality\n"
                "- Emotionally relevant to the psychology concept\n"
                f"Return ONLY a JSON array of {n} strings."
            )
        }],
    )

    try:
        raw = resp.content[0].text.strip()
        # strip optional markdown code fence
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        prompts = json.loads(raw.strip())
        logger.info("Generated %d visual prompts for: %s", len(prompts), topic)
        return prompts[:n]
    except Exception as exc:
        logger.warning("Prompt parse failed (%s) — using fallback", exc)
        return _fallback_prompts(topic, n)


def _fallback_prompts(topic: str, n: int) -> list[str]:
    """Template fallback if Claude parse fails."""
    kws = topic.split()[:3]
    base = [
        f"Person deep in thought, {' '.join(kws)}, cinematic close-up, soft bokeh",
        "Neurons firing in abstract brain visualization, dark background, glowing blue",
        "Two people in emotional conversation, shallow depth of field, warm tones",
        "Person walking alone through city at dusk, slow motion, moody atmosphere",
        "Hands writing in journal, close up, soft natural light, wooden desk",
        "Eye reflecting light, extreme macro, cinematic, psychological tension",
        "Empty room with dramatic shadow patterns, minimalist, contemplative",
        "Crowd of faces, slow motion, emotional expressions, documentary style",
        "Abstract particles forming human silhouette, dark background, blue tones",
        "Person looking at mirror reflection, conceptual, dramatic lighting",
        "Sunrise over city skyline, time lapse, new beginning, hopeful tone",
        "Clock hands spinning, time concept, macro, warm vintage tones",
    ]
    return (base * ((n // len(base)) + 1))[:n]
