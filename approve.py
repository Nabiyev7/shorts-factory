"""Telegram navbatini qayta ishlaydi (har 10 daqiqada, approve.yml).

Ikki vazifa:
  1. [✅ YouTube'ga yukla] / [🗑 Bekor] tugmalari
  2. "O'zim yasayman" rejimida siz yuborgan rasm/videolarni yig'ib, videoni yasash
"""
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402
from agents import handoff, publish_agent, render_agent  # noqa: E402
from core import state, telegram, updates  # noqa: E402

PENDING = config.STATE_DIR / "pending"
HANDOFF = config.STATE_DIR / "handoff"
TMP = config.ROOT / ".tmp_approve"
PENDING.mkdir(parents=True, exist_ok=True)
HANDOFF.mkdir(parents=True, exist_ok=True)


# ==================== 1. TASDIQLASH ====================
def fetch_video(job: dict) -> tuple[Path, Path | None]:
    local = Path(job.get("local_video", ""))
    if local.exists():
        thumb = Path(job.get("local_thumb", ""))
        return local, thumb if thumb.exists() else None

    run_id, artifact = job.get("run_id"), job.get("artifact")
    if not run_id:
        raise RuntimeError("video topilmadi (lokal fayl ham, run_id ham yo'q)")

    dest = TMP / job["uid"]
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["gh", "run", "download", str(run_id), "-n", artifact, "-D", str(dest)],
        capture_output=True, text=True,
        env={**os.environ, "GH_TOKEN": os.getenv("GH_TOKEN", os.getenv("GITHUB_TOKEN", ""))},
    )
    if p.returncode != 0:
        raise RuntimeError(f"artifact yuklab bo'lmadi: {p.stderr[-400:]}")

    vids = list(dest.rglob("*.mp4"))
    thumbs = list(dest.rglob("*.jpg"))
    if not vids:
        raise RuntimeError("artifact ichida mp4 yo'q")
    return vids[0], (thumbs[0] if thumbs else None)


def handle_approval(action: str, uid: str, cq_id: str) -> None:
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
        print(f"[approve] {uid} bekor")
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
            telegram.approve_keyboard(uid))


# ==================== 2. SIZNING RASMLARINGIZ ====================
def open_handoff() -> tuple[Path, dict] | tuple[None, None]:
    jobs = sorted(HANDOFF.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not jobs:
        return None, None
    p = jobs[-1]
    return p, json.loads(p.read_text(encoding="utf-8"))


def collect_media(job: dict) -> tuple[list[dict], list[dict], list[int]]:
    """Ish boshlangandan keyin kelgan rasm va videolarni yig'adi."""
    photos, videos, used = [], [], []
    for u in updates.media(after_ts=job["created"]):
        m = u["message"]
        used.append(u["update_id"])
        if m.get("video"):
            v = m["video"]
            videos.append({"file_id": v["file_id"], "size": v.get("file_size", 0),
                           "dur": v.get("duration", 0), "date": m["date"]})
        elif m.get("document"):
            d = m["document"]
            mime = d.get("mime_type", "")
            if mime.startswith("video/"):
                videos.append({"file_id": d["file_id"], "size": d.get("file_size", 0),
                               "dur": 0, "date": m["date"]})
            elif mime.startswith("image/"):
                photos.append({"file_id": d["file_id"], "date": m["date"]})
        elif m.get("photo"):
            biggest = sorted(m["photo"], key=lambda x: x.get("file_size", 0))[-1]
            photos.append({"file_id": biggest["file_id"], "date": m["date"]})
    photos.sort(key=lambda x: x["date"])
    videos.sort(key=lambda x: x["date"])
    return photos, videos, used


def build_from_photos(job: dict, photos: list[dict]) -> None:
    idea = job["idea"]
    work = config.OUTPUT_DIR / f"handoff_{job['uid']}"
    work.mkdir(parents=True, exist_ok=True)

    print(f"[handoff] {len(photos)} ta rasm yuklab olinmoqda…")
    paths = []
    for i, ph in enumerate(photos[:len(idea["scenes"])]):
        paths.append(telegram.download(ph["file_id"], work / f"img_{i:02d}.jpg"))

    telegram.send_message(f"🎬 {len(paths)} ta rasm qabul qilindi — video yig'ilmoqda…")
    assets = render_agent.run(idea, workdir=work, ready_images=paths)
    (work / "idea.json").write_text(json.dumps(idea, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    publish_agent.run(assets, idea)


def build_from_clips(job: dict, videos: list[dict]) -> None:
    """Google Flow / Veo / Kling kliplari -> TTS + subtitr bilan bitta Shorts."""
    idea = job["idea"]
    work = config.OUTPUT_DIR / f"handoff_{job['uid']}"
    work.mkdir(parents=True, exist_ok=True)

    telegram.send_message(f"🎞 {len(videos)} ta klip qabul qilindi — yig'ilmoqda…")
    paths = []
    for i, v in enumerate(videos[:len(idea["scenes"])]):
        if v.get("size", 0) > 19 * 1024 * 1024:
            telegram.send_message(f"⚠️ {i + 1}-klip 20 MB dan katta — o'tkazib yuborildi.")
            continue
        paths.append(telegram.download(v["file_id"], work / f"clip_{i:02d}.mp4"))

    if not paths:
        telegram.send_message("❌ Birorta klipni yuklab bo'lmadi.")
        return

    assets = render_agent.run(idea, workdir=work, ready_clips=paths)
    (work / "idea.json").write_text(json.dumps(idea, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    publish_agent.run(assets, idea)


def use_ready_video(job: dict, vid: dict) -> None:
    idea = job["idea"]
    work = config.OUTPUT_DIR / f"handoff_{job['uid']}"
    work.mkdir(parents=True, exist_ok=True)

    if vid.get("size", 0) > 19 * 1024 * 1024:
        telegram.send_message(
            "⚠️ Video 20 MB dan katta — Telegram botlari bunday faylni yuklab ololmaydi.\n"
            "Kichikroq qilib yuboring yoki rasmlarni tashlang, o'zim yig'aman.")
        return

    path = telegram.download(vid["file_id"], work / "ready.mp4")
    from core import video as vtools
    thumb = vtools.thumbnail(path, work / "thumb.jpg", at=1.0)
    telegram.send_message("🎬 Videongiz qabul qilindi — YouTube uchun tayyorlayapman…")
    publish_agent.run({"video": path, "thumb": thumb, "dir": work,
                       "duration": 0}, idea)


def process_handoff() -> None:
    path, job = open_handoff()
    if not job:
        return

    # tugmalar: "yig'" yoki "bekor"
    for u, action, uid in updates.callbacks(("build", "drop")):
        if uid != job["uid"]:
            continue
        updates.drop([u["update_id"]])
        cq = u["callback_query"]
        if action == "drop":
            telegram.answer_callback(cq["id"], "Bekor qilindi")
            telegram.send_message("🗑 Bekor qilindi.")
            path.unlink()
            return
        telegram.answer_callback(cq["id"], "Yig'ilmoqda…")
        job["force_build"] = True

    photos, videos, used = collect_media(job)
    need = job.get("need", len(job["idea"]["scenes"]))

    # --- video yo'li ---
    if videos:
        finished = len(videos) == 1 and videos[0].get("dur", 0) >= 20
        enough = len(videos) >= need or job.get("force_build")
        try:
            if finished:
                use_ready_video(job, videos[0])
            elif enough:
                build_from_clips(job, videos)
            else:
                if job.get("last_seen_v") != len(videos):
                    job["last_seen_v"] = len(videos)
                    path.write_text(json.dumps(job, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
                    telegram.send_message(
                        f"🎞 <b>{len(videos)}/{need}</b> klip keldi. Qolganini yuboring "
                        f"— yoki shu bor kliplar bilan yig'ay?",
                        keyboard=telegram.build_keyboard(job["uid"]))
                return
            updates.drop(used)
            path.unlink()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            telegram.send_message("❌ Kliplarni qayta ishlashda xato. Qaytadan yuboring.")
        return
    if not photos:
        # 6 soatdan oshsa — ishni yopamiz
        if time.time() - job["created"] > 6 * 3600:
            telegram.send_message("⌛️ Rasm kelmadi, bu g'oya yopildi.")
            path.unlink()
        return

    if len(photos) < need and not job.get("force_build"):
        if job.get("last_seen") != len(photos):      # takror yozmaslik uchun
            job["last_seen"] = len(photos)
            path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
            telegram.send_message(
                f"📥 <b>{len(photos)}/{need}</b> rasm keldi.\n"
                f"Qolganini yuboring — yoki shu bor rasmlar bilan yig'ishni "
                f"xohlasangiz tugmani bosing.",
                keyboard=telegram.build_keyboard(job["uid"]))
        return

    try:
        build_from_photos(job, photos)
        updates.drop(used)
        path.unlink()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        telegram.send_message("❌ Videoni yig'ishda xato. Rasmlarni qayta yuboring.")


# ==================== ASOSIY ====================
def main() -> None:
    updates.fetch()

    for u, action, uid in updates.callbacks(("ok", "no")):
        updates.drop([u["update_id"]])
        try:
            handle_approval(action, uid, u["callback_query"]["id"])
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    try:
        process_handoff()
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
