"""
Run this ONCE locally to generate a new refresh token with full youtube scope.
It will open a browser for you to authenticate, then print the new refresh token.

Usage:
    python scripts/reauth_youtube.py

After running, copy the printed YOUTUBE_REFRESH_TOKEN value into:
  - .env
  - GitHub Settings → Secrets → YOUTUBE_REFRESH_TOKEN
"""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

CLIENT_ID     = os.environ["YOUTUBE_CLIENT_ID"]
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]

SCOPES = [
    "https://www.googleapis.com/auth/youtube",      # full access (needed for videos.update)
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(port=0)

print("\n✓ Auth complete!\n")
print("Copy this into .env and GitHub Secrets:")
print(f"\nYOUTUBE_REFRESH_TOKEN={creds.refresh_token}\n")
