"""
One-time helper: exchange a short-lived User Access Token for a
long-lived Page Access Token, then print what to add to .env.

Steps:
  1. Go to https://developers.facebook.com/tools/explorer/
  2. Select your App, click "Generate Access Token"
  3. Add permissions: pages_manage_posts, pages_read_engagement, pages_show_list
  4. Copy the token and run:
       python get_facebook_token.py <short_lived_user_token>
"""
import sys
import requests

APP_ID     = input("Facebook App ID: ").strip()
APP_SECRET = input("Facebook App Secret: ").strip()
USER_TOKEN = sys.argv[1] if len(sys.argv) > 1 else input("Short-lived User Token: ").strip()

GRAPH = "https://graph.facebook.com/v19.0"

# Exchange for long-lived user token (60 days)
r = requests.get(f"{GRAPH}/oauth/access_token", params={
    "grant_type":        "fb_exchange_token",
    "client_id":         APP_ID,
    "client_secret":     APP_SECRET,
    "fb_exchange_token": USER_TOKEN,
})
r.raise_for_status()
ll_token = r.json()["access_token"]
print(f"\nLong-lived user token: {ll_token[:40]}...")

# List pages and their tokens
r = requests.get(f"{GRAPH}/me/accounts", params={"access_token": ll_token})
r.raise_for_status()
pages = r.json().get("data", [])

if not pages:
    print("No Pages found. Make sure your account manages a Facebook Page.")
    sys.exit(1)

print("\nYour Pages:")
for i, p in enumerate(pages):
    print(f"  [{i}] {p['name']} (id: {p['id']})")

idx = int(input("\nPick page index: "))
page = pages[idx]

print(f"\nAdd to .env:")
print(f"FACEBOOK_PAGE_ID={page['id']}")
print(f"FACEBOOK_PAGE_ACCESS_TOKEN={page['access_token']}")
print("\nPage Access Token is long-lived (~60 days). Re-run this script to refresh.")
