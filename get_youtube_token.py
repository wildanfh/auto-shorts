"""
Run once to get a valid YouTube OAuth2 refresh token.

Usage:
    python get_youtube_token.py

Then paste the printed YOUTUBE_REFRESH_TOKEN into .env
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

CLIENT_CONFIG = {
    "installed": {
        "client_id": os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

print("\n" + "=" * 60)
print("Add this to your .env:")
print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60 + "\n")
