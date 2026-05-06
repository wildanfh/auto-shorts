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
from moviepy.audio.AudioClip import AudioArrayClip, CompositeAudioClip
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
_FONT_FALLBACKS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
]
FONT_SIZE = 85           # caption font size
CHUNK     = 4            # words per caption slide
OUTLINE   = 7            # outline thickness in px
HIGHLIGHT = (255, 214, 0, 255)   # yellow for key-word highlight
MUSIC_VOL = 0.12                 # background music volume (0–1)


# ── helpers ──────────────────────────────────────────────────────────────────

def _font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    for path in [FONT_BOLD] + _FONT_FALLBACKS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
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


CLIP_DUR  = 2.0   # seconds per footage segment
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


_STOP_WORDS = {
    "the","a","an","of","and","or","why","how","what","is","are","was","were",
    "your","you","in","to","it","its","that","this","do","we","i","me","my",
    "when","if","but","so","be","been","have","has","can","will","not","our",
    "they","them","their","just","like","more","very","even","make","than",
    "also","about","would","could","should","get","got","one","two","three",
    "you've","you're","you'll","you'd","i've","i'm","i'll","i'd","it's","that's",
    "there","here","with","from","into","onto","upon","over","ever","never",
    "always","often","every","probably","something","someone","somehow","anything",
    "nothing","everything","because","actually","literally","basically","really",
    "things","thing","know","think","feel","felt","done","told","said","says",
    "doesn't","don't","didn't","won't","can't","isn't","aren't","wasn't","weren't",
    "might","some","any","many","much","most","each","both","same","other",
    "which","where","while","though","since","still","again","away","back",
    "down","then","than","too","very","well","just","only","also","even",
}


def _script_queries(script: str, n: int, topic: str) -> list[str]:
    """
    Split script into n segments; return a Pexels search query per segment.
    Scene 0 uses first-sentence (hook) keywords for an instant visual match.
    """
    words  = script.split()
    seg_sz = max(1, len(words) // n)
    stop   = _STOP_WORDS

    topic_kw = [w.lower().strip(".,!?;:\"'") for w in topic.split()
                if w.lower() not in stop and len(w) > 3]

    # First sentence = hook; its keywords drive scene 0 (min 5 chars for specificity)
    first_sent = script.split(".")[0] if "." in script else script[:60]
    hook_kws = [w.lower().strip(".,!?;:\"'") for w in first_sent.split()
                if w.lower().strip(".,!?;:\"'") not in stop
                and len(w.strip(".,!?;:\"'")) >= 5]

    queries = []
    for i in range(n):
        if i == 0:
            query = " ".join(hook_kws[:2]) if len(hook_kws) >= 2 else (
                    hook_kws[0] if hook_kws else " ".join(topic_kw[:2]) or "psychology emotion"
            )
        else:
            seg = words[i * seg_sz : (i + 1) * seg_sz]
            kws = [w.lower().strip(".,!?;:\"'") for w in seg
                   if w.lower().strip(".,!?;:\"'") not in stop
                   and len(w.strip(".,!?;:\"'")) > 3]
            query = " ".join(kws[:2]) if len(kws) >= 2 else (
                    kws[0] if kws else " ".join(topic_kw[:2]) or "psychology emotion"
            )
        queries.append(query)
        logger.debug("Scene %d query: '%s'", i, query)

    return queries


def _fetch_one_clip(query: str, idx: int, run_id: str,
                    seen_ids: set, headers: dict) -> Path | None:
    """Fetch a single portrait clip for a given query; tries fallbacks if needed."""
    import requests as req
    candidates = [query] + _FALLBACK_QUERIES
    for q in candidates:
        try:
            resp = req.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params={"query": q, "per_page": 10, "orientation": "portrait"},
                timeout=12,
            )
            resp.raise_for_status()
            videos = [v for v in resp.json().get("videos", [])
                      if v["id"] not in seen_ids]
            if not videos:
                continue
            random.shuffle(videos)
            v = videos[0]
            seen_ids.add(v["id"])
            chosen = _best_portrait_file(v.get("video_files", []))
            p = Path(f"/tmp/pexels_{run_id}_{idx}.mp4")
            _download_video(chosen["link"], p)
            logger.debug("Scene %d: '%s' → clip %s", idx, q, v["id"])
            return p
        except Exception as exc:
            logger.warning("Pexels '%s' failed: %s", q, exc)
    return None


def _pexels_paths(topic: str, run_id: str, duration: float,
                  script: str = "") -> list[Path]:
    """
    Download one portrait clip per scene, each matched to its script segment.
    Falls back to topic keywords when a segment query yields nothing.
    """
    if not PEXELS_API_KEY:
        return []

    needed  = int(duration / CLIP_DUR) + 2
    headers = {"Authorization": PEXELS_API_KEY}
    seen_ids: set = set()

    queries = _script_queries(script, needed, topic) if script else None

    if not queries:
        # legacy path: topic keywords only
        stop = _STOP_WORDS
        kws  = [w.lower().rstrip(":,;") for w in topic.split() if w.lower() not in stop]
        base = [" ".join(kws[:3]), " ".join(kws[:2]),
                kws[0] if kws else "psychology"] + _FALLBACK_QUERIES
        queries = [base[i % len(base)] for i in range(needed)]

    paths = []
    for i, q in enumerate(queries):
        p = _fetch_one_clip(q, i, run_id, seen_ids, headers)
        if p:
            paths.append(p)

    logger.info("Pexels: %d/%d scene clips fetched", len(paths), needed)
    return paths


_VIGNETTE: np.ndarray | None = None


def _vignette_mask() -> np.ndarray:
    """Cache a soft circular vignette (darkens edges, 0–1 float)."""
    global _VIGNETTE
    if _VIGNETTE is None:
        cx, cy = W / 2, H / 2
        y, x = np.ogrid[:H, :W]
        dist = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
        _VIGNETTE = np.clip(1.0 - dist * 0.55, 0.35, 1.0).astype(np.float32)
    return _VIGNETTE


def _grade_frame(frame: np.ndarray) -> np.ndarray:
    """Darken + cool tint + vignette — changes video fingerprint, adds mood."""
    f = frame.astype(np.float32)
    # cool grade: pull red down, push blue up slightly
    f[:, :, 0] *= 0.85
    f[:, :, 1] *= 0.92
    f[:, :, 2] *= 1.06
    # overall darken to ~75% brightness
    f *= 0.76
    # vignette
    v = _vignette_mask()[:, :, np.newaxis]
    f *= v
    return np.clip(f, 0, 255).astype(np.uint8)


def _assemble_footage(paths: list[Path], duration: float):
    """Trim each clip to CLIP_DUR, apply grade+flip, concatenate with crossfade."""
    segments = []
    for p in paths:
        try:
            c = VideoFileClip(str(p), audio=False).resize((W, H))
            max_start = max(0.0, c.duration - CLIP_DUR - 0.1)
            start = random.uniform(0, max_start)
            c = c.subclip(start, start + min(CLIP_DUR, c.duration))
            c = c.fl_image(_grade_frame)
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


_KLING_MAX = 4   # request at most 4 prompts; Pexels fills the rest

def _kling_paths(topic: str, run_id: str, duration: float) -> list[Path]:
    """Generate AI video clips via Kling. Returns paths or [] on failure."""
    if not KLING_AI_ACCESS_KEY:
        return []
    try:
        from src.utils.kling import generate_clips
        from src.utils.visual_prompts import generate_visual_prompts
        prompts = generate_visual_prompts(topic, n=_KLING_MAX)
        return generate_clips(prompts, run_id)
    except Exception as exc:
        logger.warning("Kling pipeline failed: %s", exc)
        return []


_CLIP_DUR_KLING = 5.0   # Kling default clip length


def _bg_clip(topic: str, run_id: str, duration: float, script: str = ""):
    # Priority: Kling AI → Pexels → gradient fallback
    for fetcher, label in [
        (lambda: _kling_paths(topic, run_id, duration), "Kling"),
        (lambda: _pexels_paths(topic, run_id, duration, script), "Pexels"),
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

_STRIP_PUNCT = str.maketrans("", "", "—–-.,!?;:\"'")


def _clean(text: str) -> str:
    return text.translate(_STRIP_PUNCT)


def _word_chunks(script: str) -> list[str]:
    """Equal-time fallback: plain text split into CHUNK-word groups."""
    words = script.split()
    return [_clean(" ".join(words[i:i + CHUNK])) for i in range(0, len(words), CHUNK)]


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
    data = json.loads(sidecar.read_text())

    if "words" in data:
        # OpenAI Whisper word-level format
        word_list: list[tuple[str, float, float]] = [
            (w["word"], w["start"], w["end"]) for w in data["words"]
        ]
    else:
        # ElevenLabs character-level format (legacy)
        chars  = data["characters"]
        starts = data["character_start_times_seconds"]
        ends   = data["character_end_times_seconds"]
        word_list = []
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
        text   = _clean(" ".join(w[0] for w in group))
        t_start = group[0][1]
        t_end   = group[-1][2]
        result.append((text, t_start, t_end))

    return result


def _beat_music(duration: float, topic: str) -> AudioArrayClip:
    """
    Royalty-free upbeat background track: kick, snare, hi-hat, bass.
    BPM and root note vary per topic. Seeded for reproducibility.
    """
    sr  = 44100
    n   = int(sr * duration) + 4   # +4 buffer prevents off-by-one
    h   = int(hashlib.md5(topic.encode()).hexdigest()[:4], 16)
    rng = np.random.default_rng(h)

    bpm  = [115, 120, 125, 128, 130, 135][h % 6]
    beat = 60.0 / bpm               # seconds per beat

    wave = np.zeros(n, dtype=np.float64)

    # Kick: sine freq-sweep 150→55 Hz, fast decay
    kd  = int(sr * 0.14)
    kenv = np.exp(-np.linspace(0, 8, kd))
    kfreq = np.linspace(150, 55, kd)
    kwav = np.sin(2 * np.pi * np.cumsum(kfreq) / sr) * kenv * 0.6
    for i in range(int(duration / beat) + 2):
        if i % 4 in (0, 2):        # beats 1 & 3
            s = int(i * beat * sr)
            if s >= n: break
            e = min(s + kd, n)
            chunk = e - s
            if chunk <= 0: continue
            wave[s:e] += kwav[:chunk]

    # Snare: noise + 200 Hz tone
    sd   = int(sr * 0.10)
    senv = np.exp(-np.linspace(0, 10, sd))
    swav = (rng.standard_normal(sd) * 0.15 +
            np.sin(2 * np.pi * 200 * np.linspace(0, 0.10, sd)) * 0.08) * senv
    for i in range(int(duration / beat) + 2):
        if i % 4 in (1, 3):        # beats 2 & 4
            s = int(i * beat * sr)
            if s >= n: break
            e = min(s + sd, n)
            chunk = e - s
            if chunk <= 0: continue
            wave[s:e] += swav[:chunk]

    # Hi-hat: short noise burst every 8th note
    hd   = int(sr * 0.025)
    henv = np.exp(-np.linspace(0, 18, hd))
    for i in range(int(duration / (beat / 2)) + 2):
        s = int(i * (beat / 2) * sr)
        if s >= n: break
        e = min(s + hd, n)
        chunk = e - s
        if chunk <= 0: continue
        wave[s:e] += rng.standard_normal(chunk) * henv[:chunk] * 0.045

    # Bass: sine on beats 1 & 3
    roots = [65.41, 69.30, 73.42, 77.78, 82.41, 87.31]   # C2–F2
    root  = roots[h % len(roots)]
    bd    = int(sr * beat * 0.75)
    benv  = np.exp(-np.linspace(0, 4, bd))
    bwav  = np.sin(2 * np.pi * root * np.linspace(0, beat * 0.75, bd)) * benv * 0.28
    for i in range(int(duration / beat) + 2):
        if i % 4 in (0, 2):
            s = int(i * beat * sr)
            if s >= n:
                break
            e = min(s + bd, n)
            chunk = e - s
            if chunk <= 0: continue
            wave[s:e] += bwav[:chunk]

    # Fade in/out 1.5 s
    fade = min(int(sr * 1.5), n // 4)
    wave[:fade]  *= np.linspace(0, 1, fade)
    wave[-fade:] *= np.linspace(1, 0, fade)

    # Normalize
    mx = np.abs(wave).max()
    if mx > 0:
        wave = wave / mx * 0.75

    stereo = np.column_stack([wave, wave]).astype(np.float32)
    return AudioArrayClip(stereo, fps=sr).set_duration(duration)


def _key_word(text: str) -> str:
    """Return the most impactful (longest non-stopword) word in a chunk."""
    stop = _STOP_WORDS
    candidates = [
        w.strip(".,!?;:\"'")
        for w in text.split()
        if w.lower().strip(".,!?;:\"'") not in stop and len(w.strip(".,!?;:\"'")) > 3
    ]
    return max(candidates, key=len) if candidates else ""


def _caption_frame(text: str) -> np.ndarray:
    """RGBA frame: transparent except big outlined caption with one word highlighted."""
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font()

    highlight = _key_word(text)

    lines   = textwrap.wrap(text, width=13) or [text]
    line_h  = FONT_SIZE + 28
    total_h = len(lines) * line_h
    y0      = H - total_h - 140

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

        # black outline for whole line
        for dx, dy in outline_offsets:
            draw.text((x + dx, y0 + dy), line, font=font, fill=(0, 0, 0, 255))
        # white fill for whole line
        draw.text((x, y0), line, font=font, fill=(255, 255, 255, 255))

        # yellow overlay for key word
        if highlight:
            prefix = ""
            for word in line.split():
                if word.strip(".,!?;:\"'") == highlight:
                    pb  = draw.textbbox((0, 0), prefix, font=font) if prefix else (0, 0, 0, 0)
                    x_h = x + (pb[2] - pb[0])
                    for dx, dy in outline_offsets:
                        draw.text((x_h + dx, y0 + dy), word, font=font, fill=(0, 0, 0, 255))
                    draw.text((x_h, y0), word, font=font, fill=HIGHLIGHT)
                    break
                prefix += word + " "

        y0 += line_h

    return np.array(img)


_HOOK_CARD_DUR = 1.6   # seconds the hook card is visible before fading


def _hook_card_frame(hook_text: str) -> np.ndarray:
    """Semi-transparent centered overlay showing the hook sentence for the first 1.6s."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(72)

    words = hook_text.split()[:14]
    text = " ".join(words)
    lines = textwrap.wrap(text, width=16) or [text]
    line_h = 72 + 22
    total_h = len(lines) * line_h

    pad = 44
    y0 = int(H * 0.28)
    rect_top = y0 - pad
    rect_bot = y0 + total_h + pad
    draw.rectangle([(pad, rect_top), (W - pad, rect_bot)], fill=(0, 0, 0, 168))

    outline_offsets = [
        (dx, dy)
        for dx in range(-5, 6, 3)
        for dy in range(-5, 6, 3)
        if dx or dy
    ]

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        for dx, dy in outline_offsets:
            draw.text((x + dx, y0 + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y0), line, font=font, fill=(255, 255, 255, 255))
        y0 += line_h

    return np.array(img)


# ── main entry ────────────────────────────────────────────────────────────────

def create_video(audio_path: Path, topic: str, script: str, run_id: str) -> Path:
    OUTPUT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_VIDEO_DIR / f"video_{run_id}.mp4"

    audio     = AudioFileClip(str(audio_path))
    total_dur = audio.duration

    bg     = _bg_clip(topic, run_id, total_dur, script)
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

    # Hook card: show first sentence prominently for the opening 1.6s
    hook_sentence = script.split(".")[0].strip() if "." in script else script[:80]
    hook_frame = _hook_card_frame(hook_sentence)
    hook_card = (
        ImageClip(hook_frame, ismask=False)
        .set_duration(_HOOK_CARD_DUR)
        .set_start(0)
        .crossfadeout(0.4)
    )

    music      = _beat_music(total_dur, topic).volumex(MUSIC_VOL)
    voice      = audio.volumex(1.5)   # boost TTS (OpenAI onyx is quiet)
    mixed_audio = CompositeAudioClip([voice, music])
    final = CompositeVideoClip([bg] + cap_clips + [hook_card], size=(W, H)).set_audio(mixed_audio)

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
