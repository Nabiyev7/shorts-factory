"""Telegram yangilanishlarining umumiy navbati.

generate va approve workflow'lari ham getUpdates ni chaqiradi. Telegram har
yangilanishni faqat bir marta beradi, shuning uchun ikkalasi bir-birinikini
"yeb qo'ymasligi" uchun hamma yangilanish shu yerdagi umumiy inbox'ga yoziladi.
"""
import json
import time

import config
from core import telegram

OFFSET_FILE = config.STATE_DIR / "tg_offset.json"
INBOX_FILE = config.STATE_DIR / "inbox.json"
MAX_AGE = 6 * 3600      # 6 soatdan eski yangilanishlar tashlab yuboriladi
MAX_ITEMS = 300


def _read(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _offset() -> int:
    return _read(OFFSET_FILE, {}).get("offset", 0)


def inbox() -> list[dict]:
    return _read(INBOX_FILE, [])


def _save_inbox(items: list[dict]) -> None:
    now = time.time()
    items = [i for i in items if now - i.get("_seen", now) < MAX_AGE][-MAX_ITEMS:]
    INBOX_FILE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def fetch() -> list[dict]:
    """Yangi yangilanishlarni olib inbox'ga qo'shadi va butun inbox'ni qaytaradi."""
    off = _offset()
    try:
        ups = telegram.get_updates(off, allowed=["callback_query", "message"])
    except Exception as e:  # noqa: BLE001
        print(f"  ! getUpdates: {e}")
        return inbox()

    items = inbox()
    known = {i.get("update_id") for i in items}
    for u in ups:
        off = max(off, u["update_id"] + 1)
        if u["update_id"] not in known:
            u["_seen"] = time.time()
            items.append(u)
    OFFSET_FILE.write_text(json.dumps({"offset": off}), encoding="utf-8")
    _save_inbox(items)
    return items


def drop(update_ids) -> None:
    """Qayta ishlangan yangilanishlarni navbatdan olib tashlaydi."""
    ids = set(update_ids)
    _save_inbox([i for i in inbox() if i.get("update_id") not in ids])


def callbacks(prefixes: tuple[str, ...]) -> list[tuple[dict, str, str]]:
    """(update, action, uid) ro'yxati — faqat kerakli prefiksdagilar."""
    out = []
    for u in inbox():
        cq = u.get("callback_query")
        if not cq:
            continue
        data = cq.get("data", "")
        if ":" not in data:
            continue
        action, uid = data.split(":", 1)
        if action in prefixes:
            out.append((u, action, uid))
    return out


def media(after_ts: float = 0) -> list[dict]:
    """Foydalanuvchi yuborgan rasm/video/fayllar."""
    out = []
    for u in inbox():
        m = u.get("message")
        if not m or m.get("date", 0) < after_ts:
            continue
        if m.get("photo") or m.get("video") or m.get("document"):
            out.append(u)
    return out
