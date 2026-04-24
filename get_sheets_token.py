"""
Run once to get OAuth2 credentials for Google Sheets.

Usage:
    python get_sheets_token.py

Saves token to config/sheets_token.json — used automatically by sheets_logger.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
from dotenv import load_dotenv
import os

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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
creds = flow.run_local_server(port=8081, prompt="consent", access_type="offline")

out = Path("config/sheets_token.json")
out.write_text(json.dumps({
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
}))

print(f"\nToken saved to {out}")
print("Google Sheets logging ready.")
