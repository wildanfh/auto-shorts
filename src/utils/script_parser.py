import re


def extract_captions(script: str, max_lines: int = 5) -> list[str]:
    """Pick short punchy sentences from script for on-screen text overlays."""
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())

    # prefer short sentences (easier to read on screen)
    scored = sorted(sentences, key=lambda s: abs(len(s.split()) - 8))
    picks = scored[:max_lines]

    # return in original script order
    order = {s: i for i, s in enumerate(sentences)}
    picks.sort(key=lambda s: order.get(s, 999))

    return [s.strip() for s in picks if s.strip()]
