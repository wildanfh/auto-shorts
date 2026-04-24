# auto-shorts

Fully automated YouTube Shorts pipeline for psychology content. Runs 3× daily, picks a topic, writes a script, generates a voiceover, assembles a video from Pexels footage, and uploads — zero manual work.

## Pipeline

```
Topic Picker → Script (Claude) → Voiceover (ElevenLabs) → Video (Pexels + MoviePy) → YouTube Upload
                                                                                    ↓
                                                              Google Sheets log + Telegram notification
```

Each stage is independently logged and non-fatal — a failure in one step does not crash subsequent runs.

## Features

- **Topic pool** — 92 evergreen psychology topics with deduplication; cycles when exhausted
- **Script** — Claude generates a 40–55 second hook-first script (shocking opening sentence, punchy close)
- **Voiceover** — ElevenLabs with word-level timestamp alignment for precise caption sync
- **Video**
  - Pexels portrait footage, one unique clip per script segment (footage matches narration)
  - Clips cut every 2 seconds — fast-paced Shorts style
  - Bold CapCut-style captions, most impactful word highlighted in yellow per chunk
  - Ambient background music generated per video (royalty-free, copyright-safe)
- **Upload** — YouTube OAuth2 resumable upload, title format `Psychology #N: <topic>`
- **Analytics** — views, likes, comments, avg view duration fetched 24 h after upload → written back to Sheets
- **Notifications** — Telegram summary after every run

## Requirements

- Python 3.10+
- `ffmpeg` installed (`sudo apt install ffmpeg`)
- A font at `/usr/share/fonts/fonts-go/Go-Bold.ttf` (or edit `FONT_BOLD` in `video_creator.py`)

```bash
pip install -r requirements.txt
```

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `ELEVENLABS_API_KEY` | [elevenlabs.io](https://elevenlabs.io) → Profile |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice library (default: Adam = `pNInz6obpgDQGcFmaJgB`) |
| `YOUTUBE_CLIENT_ID` / `SECRET` | Google Cloud Console → OAuth 2.0 credentials |
| `YOUTUBE_REFRESH_TOKEN` | Run `python get_youtube_token.py` (see below) |
| `GOOGLE_SHEET_ID` | From the Google Sheets URL |
| `PEXELS_API_KEY` | [pexels.com/api](https://www.pexels.com/api/) (free) |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Your Telegram user or group ID |

### 2. YouTube OAuth token

Enable **YouTube Data API v3** and **YouTube Analytics API** in [Google Cloud Console](https://console.cloud.google.com), then:

```bash
python get_youtube_token.py
```

A browser window opens. Approve the scopes, then paste the printed token into `.env` as `YOUTUBE_REFRESH_TOKEN`.

### 3. Google Sheets token

Enable **Google Sheets API** in Google Cloud Console, then:

```bash
python get_sheets_token.py
```

This writes `config/sheets_token.json`. The token auto-refreshes on each run.

## Usage

**Run once immediately:**

```bash
python main.py --now
```

**Run on schedule (08:00, 14:00, 20:00 local time):**

```bash
python main.py
```

**Cron (recommended for production):**

```bash
crontab -e
# add:
0 8,14,20 * * * /home/<user>/code/auto-shorts/cron_run.sh >> logs/cron.log 2>&1
```

## Project structure

```
auto-shorts/
├── main.py                      # Entry point + scheduler
├── cron_run.sh                  # Cron wrapper (loads .env, runs main.py --now)
├── config/
│   └── settings.py              # All env vars and constants
├── data/
│   ├── topics.json              # Evergreen psychology topic pool (92 topics)
│   ├── used_topics.json         # Deduplication log
│   ├── series_counter.json      # Episode counter for video titles
│   └── analytics_pending.json   # Queue for 24 h analytics fetch
├── src/
│   ├── pipeline/
│   │   ├── runner.py            # Orchestrates all pipeline stages
│   │   ├── topic_picker.py      # Random pick with deduplication
│   │   ├── script_generator.py  # Claude script generation
│   │   ├── voiceover.py         # ElevenLabs TTS + timestamp sidecar
│   │   ├── video_creator.py     # Footage fetch, caption render, music mix
│   │   ├── youtube_uploader.py  # OAuth2 resumable upload
│   │   └── sheets_logger.py     # Google Sheets run log + analytics update
│   └── utils/
│       ├── analytics_fetcher.py # YouTube Analytics API client
│       ├── kling.py             # Kling AI video generation client (optional)
│       ├── visual_prompts.py    # Claude-generated Kling prompts
│       ├── telegram.py          # Telegram notification sender
│       └── logger.py            # Per-run log file setup
├── get_youtube_token.py         # One-time OAuth2 token helper
└── get_sheets_token.py          # One-time Sheets token helper
```

## Output

Each run produces:
- `output/audio/voiceover_<run_id>.mp3` + `.json` sidecar (word timestamps)
- `output/video/video_<run_id>.mp4`
- `logs/run_<run_id>.log`

## Optional: Kling AI footage

If you have a [Kling AI](https://klingai.com) API key, the pipeline will generate AI video clips instead of Pexels stock footage. Add to `.env`:

```
KLING_AI_ACCESS_KEY=...
KLING_AI_SECRET_KEY=...
```

Kling clips are capped at 4 per video to stay within rate limits. Pexels fills the remaining duration.

## Monetization path

YouTube Partner Program (Shorts) requires:
- **Tier 1** (basic): 500 subscribers + 3M Shorts views in 12 months
- **Tier 2** (ads): 1,000 subscribers + 10M Shorts views in 90 days

At 3 videos/day with average 10k views each → ~900k views/month. Tier 1 is reachable in 3–4 months with consistent posting and strong hooks.
