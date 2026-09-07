"""Telegram Bot API — video yuborish, tugmalar, callback'larni o'qish."""
import json
from pathlib import Path

import requests

import config

API = "https://api.telegram.org/bot{token}/{method}"


def _call(method: str, *, files=None, **data) -> dict:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN yo'q")
    payload = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
               for k, v in data.items() if v is not None}
    r = requests.post(API.format(token=config.TELEGRAM_BOT_TOKEN, method=method),
                      data=payload, files=files, timeout=600)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"Telegram {method}: {j}")
    return j["result"]


def approve_keyboard(uid: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ YouTube'ga yukla", "callback_data": f"ok:{uid}"},
        {"text": "🗑 Bekor", "callback_data": f"no:{uid}"},
    ]]}


def send_video(video: Path, caption: str, keyboard: dict | None = None) -> dict:
    with open(video, "rb") as f:
        return _call("sendVideo",
                     files={"video": (video.name, f, "video/mp4")},
                     chat_id=config.TELEGRAM_CHAT_ID,
                     caption=caption[:1024],
                     parse_mode="HTML",
                     supports_streaming="true",
                     reply_markup=keyboard)


def send_message(text: str, reply_to: int | None = None) -> dict:
    return _call("sendMessage", chat_id=config.TELEGRAM_CHAT_ID,
                 text=text[:4096], parse_mode="HTML",
                 reply_to_message_id=reply_to,
                 link_preview_options={"is_disabled": True})


def edit_caption(message_id: int, caption: str, keyboard: dict | None = None) -> dict:
    return _call("editMessageCaption", chat_id=config.TELEGRAM_CHAT_ID,
                 message_id=message_id, caption=caption[:1024],
                 parse_mode="HTML", reply_markup=keyboard)


def answer_callback(cq_id: str, text: str) -> None:
    try:
        _call("answerCallbackQuery", callback_query_id=cq_id, text=text[:200])
    except Exception as e:  # noqa: BLE001
        print(f"  ! answerCallbackQuery: {e}")


def get_updates(offset: int, timeout: int = 0) -> list[dict]:
    return _call("getUpdates", offset=offset, timeout=timeout,
                 allowed_updates=["callback_query"])
