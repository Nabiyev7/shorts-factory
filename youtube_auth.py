"""Bir martalik YouTube OAuth.

Oldindan: Google Cloud Console -> APIs -> YouTube Data API v3 yoqing ->
Credentials -> OAuth client ID -> "Desktop app" -> JSON yuklab oling ->
loyiha papkasiga `client_secret.json` nomi bilan qo'ying.
Audience -> Test users -> o'z gmail'ingizni qo'shing.

Ishga tushiring:  python youtube_auth.py
"""
import json

from google_auth_oauthlib.flow import InstalledAppFlow

import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

if __name__ == "__main__":
    if not config.YOUTUBE_CLIENT_SECRET.exists():
        raise SystemExit(f"Topilmadi: {config.YOUTUBE_CLIENT_SECRET}")

    flow = InstalledAppFlow.from_client_secrets_file(str(config.YOUTUBE_CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    config.YOUTUBE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    cs = json.loads(config.YOUTUBE_CLIENT_SECRET.read_text())
    info = cs.get("installed") or cs.get("web") or {}

    print(f"\n✅ Lokal token saqlandi: {config.YOUTUBE_TOKEN_FILE}")
    print("\n" + "=" * 64)
    print("  GitHub -> Settings -> Secrets and variables -> Actions")
    print("  quyidagi 3 ta secret'ni qo'shing:")
    print("=" * 64)
    print(f"YOUTUBE_CLIENT_ID            = {info.get('client_id', '?')}")
    print(f"YOUTUBE_CLIENT_SECRET_VALUE  = {info.get('client_secret', '?')}")
    print(f"YOUTUBE_REFRESH_TOKEN        = {creds.refresh_token}")
    print("=" * 64)
