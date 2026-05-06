"""
Fix all video titles that have redundant prefixes (e.g. "Your brain is lying to you about Why X").
Run AFTER reauth_youtube.py has updated YOUTUBE_REFRESH_TOKEN in .env.

Usage:
    python scripts/fix_titles.py [--dry-run]
"""
import argparse
import os
import time
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

FIXES = {
    # video_id: clean title
    "CDz8jSExsmk": "Why your brain exaggerates the future 🧠",
    "YMc8Y60sh9c": "Why humans fear uncertainty more than pain 🧠",
    "5KiRg5-2NZk": "The psychology of color in marketing 🧠",
    "JUwMmp7nNlw": "Why we cry at movies but not real tragedies 🧠",
    "mkjr1sRdRgA": "How the words you use shape your reality 🧠",
    "lf-lHI3lIGM": "The psychology of guilt vs shame and why it matters 🧠",
    "hfw6KKjgQ4M": "The psychology of regret and how to stop living in it 🧠",
    "B8Yu9Jr7c6M": "Why we feel more pain when we think we should 🧠",
    "0Qq2nz8vfus": "Why you're bad at predicting your future emotions 🧠",
    "3yFZCxYat7U": "The science of fear and why you are addicted to it 🧠",
    "kyBhRHKqKMs": "Why your brain treats social rejection like physical pain 🧠",
    "l5Gjs4I_m4E": "How your gut feeling is actually math 🧠",
    "KUGVVdoIGyQ": "Why your brain is optimized for survival not happiness 🧠",
    "jaYSkoi6Upg": "Why you make worse decisions when tired 🧠",
    "GWS-AvirALQ": "Why your brain cannot tell real from imagined 🧠",
    "w5ebnDplsUc": "Why you remember embarrassing moments forever 🧠",
    "gr7WKvlVRoA": "How your environment secretly shapes your behavior 🧠",
    "SSN1YOy1CzY": "How the placebo effect rewires your brain 🧠",
    "vobqib6hTZU": "Why making decisions exhausts your brain 🧠",
    "hXOylfaRFao": "How your brain physically changes when you fall in love 🧠",
    "Y5H8-_CiVJ0": "Why you forget names immediately after hearing them 🧠",
    "6fZStDO8Ah4": "How stress physically shrinks your brain 🧠",
    "AFTT1A_w78M": "Confirmation bias and your information bubble 🧠",
    "R1jw5BYOri0": "How your birth order shapes your personality 🧠",
    "TQ13S5q_cMg": "The psychology of crying and why it feels good 🧠",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print changes without applying")
    args = parser.parse_args()

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    ok = fail = 0
    for vid_id, new_title in FIXES.items():
        if args.dry_run:
            print(f"[DRY] {vid_id}: {new_title}")
            ok += 1
            continue
        try:
            yt.videos().update(
                part="snippet",
                body={"id": vid_id, "snippet": {"title": new_title, "categoryId": "27"}},
            ).execute()
            print(f"✓ {vid_id}: {new_title}")
            ok += 1
        except Exception as e:
            print(f"✗ {vid_id}: {e}")
            fail += 1
        time.sleep(0.5)

    print(f"\nDone: {ok} updated, {fail} failed")


if __name__ == "__main__":
    main()
