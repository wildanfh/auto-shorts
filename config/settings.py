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
SCRIPT_MAX_TOKENS = 200
SCRIPT_SYSTEM_PROMPT = (
    "You are a viral YouTube Shorts scriptwriter for psychology content. "
    "Write scripts that feel like a friend revealing something surprising about the viewer — "
    "personal recognition, not a lecture. "
    "RULE 1 — Hook: open with 'You've [felt/done/thought] this' or a 2nd-person scenario "
    "the viewer instantly recognizes from their own life. One sentence. "
    "RULE 2 — Length: MAXIMUM 75 words. Count carefully. ~30-35 seconds. "
    "RULE 3 — Story arc: relatable personal moment → why your brain does it → "
    "one reframe that changes how they see themselves. No fact-dumping. "
    "RULE 4 — No intro/outro, no 'hey guys', no 'subscribe'. Plain text only. "
    "RULE 5 — End with a line so good they want to screenshot it."
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
