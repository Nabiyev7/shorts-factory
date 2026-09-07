"""Tasdiqlash ishlovchisi.

Telegramdagi "✅ YouTube'ga yukla" / "🗑 Bekor" tugmalarini o'qiydi va
tasdiqlangan videolarni YouTube'ga yuklaydi.

GitHub Actions'da har 10 daqiqada ishlaydi (approve.yml).
Lokalda ham ishlaydi: python approve.py
"""
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402
from agents import publish_agent  # noqa: E402
from core import state, telegram  # noqa: E402

PENDING = config.STATE_DIR / "pending"
OFFSET_FILE = config.STATE_DIR / "tg_offset.json"
TMP = config.ROOT / ".tmp_approve"


def _offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return json.loads(OFFSET_FILE.read_text())["offset"]
        except Exception:  # noqa: BLE001
            return 0
    return 0


def _save_offset(v: int) -> None:
    OFFSET_FILE.write_text(json.dumps({"offset": v}), encoding="utf-8")


def fetch_video(job: dict) -> tuple[Path, Path | None]:
    """Videoni topadi: avval lokal, bo'lmasa GitHub artifact'dan yuklab oladi."""
    local = Path(job.get("local_video", ""))
    if local.exists():
        thumb = Path(job.get("local_thumb", ""))
        return local, thumb if thumb.exists() else None

    run_id, artifact = job.get("run_id"), job.get("artifact")
    if not run_id:
        raise RuntimeError("video topilmadi (lokal fayl ham, run_id ham yo'q)")

    dest = TMP / job["uid"]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["gh", "run", "download", str(run_id), "-n", artifact, "-D", str(dest)],
        capture_output=True, text=True,
        env={**os.environ, "GH_TOKEN": os.getenv("GH_TOKEN", os.getenv("GITHUB_TOKEN", ""))},
    )
    if p.returncode != 0:
        raise RuntimeError(f"artifact yuklab bo'lmadi (90 kundan oshgan bo'lishi mumkin): {p.stderr[-500:]}")

    vids = list(dest.rglob("*.mp4"))
    thumbs = list(dest.rglob("*.jpg"))
    if not vids:
        raise RuntimeError("artifact ichida mp4 yo'q")
    return vids[0], (thumbs[0] if thumbs else None)


def handle(action: str, uid: str, cq_id: str) -> None:
    path = PENDING / f"{uid}.json"
    if not path.exists():
        telegram.answer_callback(cq_id, "Bu video allaqachon ko'rib chiqilgan")
        return
    job = json.loads(path.read_text(encoding="utf-8"))
    idea = job["idea"]

    if action == "no":
        telegram.answer_callback(cq_id, "Bekor qilindi")
        telegram.edit_caption(job["message_id"],
                              publish_agent.caption(idea, "\n\n🗑 <i>Bekor qilindi</i>"), None)
        path.unlink()
        print(f"[approve] {uid} bekor qilindi")
        return

    telegram.answer_callback(cq_id, "Yuklanmoqda…")
    telegram.edit_caption(job["message_id"],
                          publish_agent.caption(idea, "\n\n⬆️ <i>YouTube'ga yuklanmoqda…</i>"), None)
    try:
        video, thumb = fetch_video(job)
        vid = publish_agent.to_youtube(video, idea, thumb)
        telegram.edit_caption(job["message_id"],
                              publish_agent.caption(idea, f"\n\n▶️ https://youtu.be/{vid}"), None)
        state.add({"title": idea["youtube_title"], "topic": idea["topic"],
                   "youtube_id": vid, "uid": uid})
        path.unlink()
        print(f"[approve] {uid} -> https://youtu.be/{vid}")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        telegram.edit_caption(
            job["message_id"],
            publish_agent.caption(idea, f"\n\n❌ <i>Xato: {str(e)[:180]}</i>"),
            telegram.approve_keyboard(uid),
        )


def main() -> None:
    off = _offset()
    updates = telegram.get_updates(off)
    if not updates:
        print("[approve] yangi tugma bosilishi yo'q")
        return

    for u in updates:
        off = max(off, u["update_id"] + 1)
        cq = u.get("callback_query")
        if not cq:
            continue
        data = cq.get("data", "")
        if ":" not in data:
            continue
        action, uid = data.split(":", 1)
        if action not in ("ok", "no"):
            continue
        try:
            handle(action, uid, cq["id"])
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    _save_offset(off)
    if TMP.exists():
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
