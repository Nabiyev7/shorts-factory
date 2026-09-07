"""AGENT 3 — Telegramga tashlaydi (tasdiqlash tugmalari bilan) + YouTube'ga yuklaydi."""
import json
import os
import uuid
from pathlib import Path

import config
from core import telegram

PENDING_DIR = config.STATE_DIR / "pending"
PENDING_DIR.mkdir(parents=True, exist_ok=True)


def caption(idea: dict, extra: str = "") -> str:
    tags = " ".join("#" + t.replace(" ", "").replace("-", "") for t in idea["tags"][:6])
    return (f"🎬 <b>{idea['youtube_title']}</b>\n\n"
            f"{idea['youtube_description']}\n\n{tags}{extra}")


# ---------------- YouTube ----------------
def yt_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]

    if config.YT_REFRESH_TOKEN and config.YT_CLIENT_ID:
        creds = Credentials(
            token=None,
            refresh_token=config.YT_REFRESH_TOKEN,
            client_id=config.YT_CLIENT_ID,
            client_secret=config.YT_CLIENT_SECRET_VAL,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=scopes,
        )
        creds.refresh(Request())
    elif config.YOUTUBE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.YOUTUBE_TOKEN_FILE), scopes)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            config.YOUTUBE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    else:
        raise RuntimeError("YouTube kaliti yo'q: youtube_token.json yoki YOUTUBE_REFRESH_TOKEN kerak")

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def to_youtube(video: Path, idea: dict, thumb: Path | None = None) -> str:
    from googleapiclient.http import MediaFileUpload

    yt = yt_service()
    body = {
        "snippet": {
            "title": idea["youtube_title"][:100],
            "description": idea["youtube_description"][:4900],
            "tags": idea["tags"][:20],
            "categoryId": "27",
        },
        "status": {"privacyStatus": config.YOUTUBE_PRIVACY,
                   "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    yuklanmoqda… {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"[3] YouTube ✅ https://youtu.be/{vid}")

    if thumb and Path(thumb).exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:  # noqa: BLE001
            print(f"    ! thumbnail: {e}")
    return vid


# ---------------- Asosiy ----------------
def run(assets: dict, idea: dict) -> dict:
    """APPROVAL_MODE=true -> Telegramga tugmalar bilan, YouTube kutadi.
    false -> darhol YouTube + Telegram."""
    if config.APPROVAL_MODE:
        uid = uuid.uuid4().hex[:10]
        msg = telegram.send_video(
            assets["video"],
            caption(idea, "\n\n⏳ <i>Tasdiqni kutmoqda</i>"),
            telegram.approve_keyboard(uid),
        )
        pending = {
            "uid": uid,
            "message_id": msg["message_id"],
            "run_id": os.getenv("GITHUB_RUN_ID", ""),
            "artifact": f"short-{uid}",
            "video_name": Path(assets["video"]).name,
            "local_video": str(assets["video"]),
            "local_thumb": str(assets.get("thumb", "")),
            "idea": idea,
        }
        (PENDING_DIR / f"{uid}.json").write_text(
            json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[3] Telegramga yuborildi, tasdiq kutilmoqda (uid={uid})")
        return {"uid": uid, "pending": True, "youtube_id": None}

    vid = None
    try:
        if config.YOUTUBE_ENABLED:
            vid = to_youtube(assets["video"], idea, assets.get("thumb"))
    except Exception as e:  # noqa: BLE001
        print(f"[3] ! YouTube xato: {e}")
    try:
        telegram.send_video(assets["video"],
                            caption(idea, f"\n\n▶️ https://youtu.be/{vid}" if vid else ""))
        print("[3] Telegram ✅")
    except Exception as e:  # noqa: BLE001
        print(f"[3] ! Telegram xato: {e}")
    return {"youtube_id": vid, "pending": False}
