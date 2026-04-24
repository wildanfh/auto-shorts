"""
Generates original YouTube Shorts video locally.

Background : Pexels portrait stock video (needs PEXELS_API_KEY) or
             animated gradient with slow pan (no extra API needed).
Captions   : 4-word CapCut-style chunks — large white bold text,
             thick black outline, bottom-center. No clutter.
"""
import hashlib
import logging
import random
import textwrap
from pathlib import Path

import numpy as np
import PIL.Image
# MoviePy uses the removed ANTIALIAS constant — patch for Pillow >= 10
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)

from config.settings import OUTPUT_VIDEO_DIR, PEXELS_API_KEY, KLING_AI_ACCESS_KEY

logger = logging.getLogger(__name__)

W, H      = 1080, 1920
FONT_BOLD = "/usr/share/fonts/fonts-go/Go-Bold.ttf"
FONT_SIZE = 85           # caption font size
CHUNK     = 4            # words per caption slide
OUTLINE   = 7            # outline thickness in px


# ── helpers ──────────────────────────────────────────────────────────────────

def _font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except OSError:
        return ImageFont.load_default()


def _topic_colors(topic: str) -> tuple:
    h = hashlib.md5(topic.encode()).hexdigest()
    def clamp(v, lo, hi): return max(lo, min(hi, v))
    c1 = (clamp(int(h[0:2],16)%130+20,15,210),
          clamp(int(h[2:4],16)%100+10,10,180),
          clamp(int(h[4:6],16)%150+60,60,230))
    c2 = (clamp(int(h[6:8],16)%110+10,10,190),
          clamp(int(h[8:10],16)%90+20,15,170),
          clamp(int(h[10:12],16)%130+50,40,210))
    return c1, c2


# ── background ───────────────────────────────────────────────────────────────

def _gradient_pan_clip(topic: str, duration: float):
    """
    Animated gradient: 1.18× oversized canvas,
    slow diagonal pan → looks like Ken Burns on abstract art.
    """
    scale  = 1.18
    lw, lh = int(W * scale), int(H * scale)
    c1, c2 = _topic_colors(topic)

    canvas = np.zeros((lh, lw, 3), dtype=np.uint8)
    for ch in range(3):
        row = np.linspace(c1[ch], c2[ch], lh, dtype=np.float32)
        canvas[:, :, ch] = row[:, np.newaxis].astype(np.uint8)

    max_x = lw - W
    max_y = lh - H

    def make_frame(t):
        p  = t / duration
        x  = int(max_x * p)
        y  = int(max_y * p * 0.4)
        return canvas[y:y + H, x:x + W]

    return VideoClip(make_frame, duration=duration).set_fps(30)


CLIP_DUR  = 3.5   # seconds per footage segment
CLIP_FADE = 0.25  # crossfade between segments

# Fallback queries used when topic keywords don't yield enough clips
_FALLBACK_QUERIES = [
    "person thinking", "human brain mind", "psychology people",
    "emotions feelings", "mindset focus", "abstract motion",
]


def _best_portrait_file(files: list) -> dict:
    portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    pool = sorted(portrait or files, key=lambda f: f.get("height", 0))
    return pool[min(1, len(pool) - 1)]


def _download_video(url: str, path: Path) -> None:
    import requests as req
    with req.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as fp:
            for chunk in r.iter_content(8192):
                fp.write(chunk)


def _pexels_search(query: str, seen_ids: set, headers: dict) -> list[dict]:
    """Single Pexels search, returns videos not already in seen_ids."""
    import requests as req
    resp = req.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params={"query": query, "per_page": 15, "orientation": "portrait"},
        timeout=12,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    fresh  = [v for v in videos if v["id"] not in seen_ids]
    random.shuffle(fresh)
    return fresh


def _pexels_paths(topic: str, run_id: str, duration: float) -> list[Path]:
    """
    Download enough unique portrait clips to cover `duration` without repeating.
    Tries topic keywords first, then progressively broader fallback queries.
    """
    if not PEXELS_API_KEY:
        return []

    needed = int(duration / CLIP_DUR) + 2   # clips needed to fill duration

    stop  = {"the","a","an","of","and","or","why","how","what","is","are",
             "your","you","in","to","it","its","that","this","do"}
    kws   = [w.lower().rstrip(":,;") for w in topic.split() if w.lower() not in stop]
    queries = [
        " ".join(kws[:3]),
        " ".join(kws[:2]),
        kws[0] if kws else "psychology",
    ] + _FALLBACK_QUERIES

    headers  = {"Authorization": PEXELS_API_KEY}
    seen_ids: set = set()
    video_pool: list[dict] = []

    for q in queries:
        if len(video_pool) >= needed:
            break
        try:
            fresh = _pexels_search(q, seen_ids, headers)
            for v in fresh:
                seen_ids.add(v["id"])
            video_pool += fresh
            logger.debug("Pexels query '%s' → %d fresh clips", q, len(fresh))
        except Exception as exc:
            logger.warning("Pexels query '%s' failed: %s", q, exc)

    paths = []
    for i, v in enumerate(video_pool[:needed]):
        try:
            chosen = _best_portrait_file(v.get("video_files", []))
            p = Path(f"/tmp/pexels_{run_id}_{i}.mp4")
            _download_video(chosen["link"], p)
            paths.append(p)
        except Exception as exc:
            logger.warning("Download failed (video %s): %s", v.get("id"), exc)

    logger.info("Pexels: %d unique clips fetched (need %d for %.0fs)",
                len(paths), needed, duration)
    return paths


def _assemble_footage(paths: list[Path], duration: float):
    """Trim each clip to CLIP_DUR, concatenate with crossfade — no repeats."""
    segments = []
    for p in paths:
        try:
            c = VideoFileClip(str(p), audio=False).resize((W, H))
            max_start = max(0.0, c.duration - CLIP_DUR - 0.1)
            start = random.uniform(0, max_start)
            c = c.subclip(start, start + min(CLIP_DUR, c.duration))
            segments.append(c)
        except Exception as exc:
            logger.warning("Skipping clip %s: %s", p, exc)

    if not segments:
        return None

    # no repeat — if still short, last clip just holds (subclip handles it)
    pool = segments

    # crossfade between segments
    faded = [pool[0]]
    for c in pool[1:]:
        faded.append(c.crossfadein(CLIP_FADE))

    result = concatenate_videoclips(faded, method="compose", padding=-CLIP_FADE)
    return result.subclip(0, duration)


def _kling_paths(topic: str, run_id: str, duration: float) -> list[Path]:
    """Generate AI video clips via Kling. Returns paths or [] on failure."""
    if not KLING_AI_ACCESS_KEY:
        return []
    try:
        from src.utils.kling import generate_clips
        from src.utils.visual_prompts import generate_visual_prompts
        n       = int(duration / float(_CLIP_DUR_KLING)) + 2
        prompts = generate_visual_prompts(topic, n=n)
        return generate_clips(prompts, run_id)
    except Exception as exc:
        logger.warning("Kling pipeline failed: %s", exc)
        return []


_CLIP_DUR_KLING = 5.0   # Kling default clip length


def _bg_clip(topic: str, run_id: str, duration: float):
    # Priority: Kling AI → Pexels → gradient fallback
    for fetcher, label in [
        (lambda: _kling_paths(topic, run_id, duration), "Kling"),
        (lambda: _pexels_paths(topic, run_id, duration), "Pexels"),
    ]:
        paths = fetcher()
        if paths:
            try:
                clip = _assemble_footage(paths, duration)
                if clip:
                    logger.info("Background source: %s (%d clips)", label, len(paths))
                    return clip
            except Exception as exc:
                logger.warning("%s assemble failed: %s", label, exc)

    return _gradient_pan_clip(topic, duration)


# ── caption timing ───────────────────────────────────────────────────────────

def _word_chunks(script: str) -> list[str]:
    """Equal-time fallback: plain text split into CHUNK-word groups."""
    words = script.split()
    return [" ".join(words[i:i + CHUNK]) for i in range(0, len(words), CHUNK)]


def _timed_chunks(audio_path: Path, script: str, total_dur: float
                  ) -> list[tuple[str, float, float]]:
    """
    Returns list of (text, start_sec, end_sec) using ElevenLabs alignment sidecar.
    Falls back to equal-time split if sidecar missing.
    """
    sidecar = audio_path.with_suffix(".json")
    if not sidecar.exists():
        chunks = _word_chunks(script)
        seg = total_dur / len(chunks)
        return [(c, i * seg, (i + 1) * seg) for i, c in enumerate(chunks)]

    import json
    data   = json.loads(sidecar.read_text())
    chars  = data["characters"]
    starts = data["character_start_times_seconds"]
    ends   = data["character_end_times_seconds"]

    # build word-level timing
    word_list: list[tuple[str, float, float]] = []
    buf, w_start = [], None
    for ch, ts, te in zip(chars, starts, ends):
        if ch in (" ", "\n"):
            if buf:
                word_list.append(("".join(buf), w_start, te))
                buf, w_start = [], None
        else:
            if not buf:
                w_start = ts
            buf.append(ch)
    if buf:
        word_list.append(("".join(buf), w_start, ends[-1]))

    # group into CHUNK-word segments
    result = []
    for i in range(0, len(word_list), CHUNK):
        group  = word_list[i:i + CHUNK]
        text   = " ".join(w[0] for w in group)
        t_start = group[0][1]
        t_end   = group[-1][2]
        result.append((text, t_start, t_end))

    return result


def _caption_frame(text: str) -> np.ndarray:
    """RGBA frame: transparent except bottom gradient + big outlined caption."""
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font()

    # dark gradient bar bottom 35%
    bar_top = int(H * 0.65)
    for y in range(bar_top, H):
        a = int(210 * (y - bar_top) / (H - bar_top))
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    # word-wrap at 13 chars/line to keep text big
    lines   = textwrap.wrap(text, width=13) or [text]
    line_h  = FONT_SIZE + 28
    total_h = len(lines) * line_h
    y0      = H - total_h - 140   # 140px from bottom edge

    outline_offsets = [
        (dx, dy)
        for dx in range(-OUTLINE, OUTLINE + 1, 3)
        for dy in range(-OUTLINE, OUTLINE + 1, 3)
        if dx or dy
    ]

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw   = bbox[2] - bbox[0]
        x    = (W - tw) // 2

        # black outline
        for dx, dy in outline_offsets:
            draw.text((x + dx, y0 + dy), line, font=font, fill=(0, 0, 0, 255))
        # white fill
        draw.text((x, y0), line, font=font, fill=(255, 255, 255, 255))
        y0 += line_h

    return np.array(img)


# ── main entry ────────────────────────────────────────────────────────────────

def create_video(audio_path: Path, topic: str, script: str, run_id: str) -> Path:
    OUTPUT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_VIDEO_DIR / f"video_{run_id}.mp4"

    audio     = AudioFileClip(str(audio_path))
    total_dur = audio.duration

    bg     = _bg_clip(topic, run_id, total_dur)
    timed  = _timed_chunks(audio_path, script, total_dur)

    cap_clips = []
    for text, t_start, t_end in timed:
        dur   = max(t_end - t_start, 0.1)
        frame = _caption_frame(text)
        clip  = (
            ImageClip(frame, ismask=False)
            .set_duration(dur)
            .set_start(t_start)
            .crossfadein(0.08)
        )
        cap_clips.append(clip)

    final = CompositeVideoClip([bg] + cap_clips, size=(W, H)).set_audio(audio)

    final.write_videofile(
        str(out_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger=None,
    )

    size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Video created: %s (%.1f MB)", out_path, size_mb)
    return out_path
