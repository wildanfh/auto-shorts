import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# API keys
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]
CREATOMATE_API_KEY = os.environ["CREATOMATE_API_KEY"]
CREATOMATE_TEMPLATE_ID = os.environ["CREATOMATE_TEMPLATE_ID"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]

# Paths
OUTPUT_AUDIO_DIR = BASE_DIR / "output" / "audio"
OUTPUT_VIDEO_DIR = BASE_DIR / "output" / "video"
LOGS_DIR = BASE_DIR / "logs"
TOPICS_FILE = BASE_DIR / "data" / "topics.json"
USED_TOPICS_FILE = BASE_DIR / "data" / "used_topics.json"

# Claude
CLAUDE_MODEL = "claude-sonnet-4-6"
SCRIPT_MAX_TOKENS = 300
SCRIPT_SYSTEM_PROMPT = (
    "You are a viral YouTube Shorts scriptwriter specializing in psychology. "
    "RULE 1 — Hook: open with ONE sentence that is a shocking claim, counterintuitive fact, "
    "or provocative question about the topic. It must make the viewer stop scrolling instantly. "
    "RULE 2 — Pacing: 40-55 seconds when spoken at ~120-130 wpm. "
    "RULE 3 — No intro/outro, no 'hey guys', no 'subscribe'. Plain text only, no stage directions. "
    "RULE 4 — End with a punchy 1-sentence insight the viewer will remember."
)

# YouTube
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs
YOUTUBE_PRIVACY = "public"  # public | unlisted | private
YOUTUBE_TAGS = ["psychology", "shorts", "mindset", "science", "facts"]

# Pexels (optional — stock video backgrounds)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Kling AI (optional — AI-generated video backgrounds, overrides Pexels when set)
KLING_AI_ACCESS_KEY = os.getenv("KLING_AI_ACCESS_KEY", "")
KLING_AI_SECRET_KEY = os.getenv("KLING_AI_SECRET_KEY", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
