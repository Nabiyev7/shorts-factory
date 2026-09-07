"""AGENT 2 — Nano Banana rasm + edge-tts ovoz + subtitr + ffmpeg -> mp4."""
import random
import re
from datetime import datetime
from pathlib import Path

import config
from core import images, subtitles, tts, video


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "short"


def _pick_music() -> Path | None:
    files = [p for p in config.MUSIC_DIR.glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg")]
    return random.choice(files) if files else None


def run(idea: dict, workdir: Path | None = None) -> dict:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slug(idea.get("slug") or idea["topic"])
    work = workdir or (config.OUTPUT_DIR / f"{stamp}_{slug}")
    work.mkdir(parents=True, exist_ok=True)

    scenes = idea["scenes"]
    img_paths, durs, audio_paths, all_words = [], [], [], []
    cursor = 0.0

    for i, sc in enumerate(scenes):
        print(f"[2] Sahna {i + 1}/{len(scenes)} — rasm...")
        img = images.generate(sc["image_prompt"], work / f"img_{i:02d}.png")

        print(f"[2] Sahna {i + 1}/{len(scenes)} — ovoz...")
        mp3 = work / f"aud_{i:02d}.mp3"
        dur, words = tts.speak(sc["narration"], mp3)

        for w in words:
            all_words.append({"text": w["text"], "start": w["start"] + cursor,
                              "end": min(w["end"] + cursor, cursor + dur)})
        cursor += dur
        img_paths.append(img)
        durs.append(dur)
        audio_paths.append(mp3)

    total = sum(durs)
    if total > config.MAX_DURATION:
        print(f"    ! {total:.1f}s > {config.MAX_DURATION}s — oxirgi sahna(lar) kesildi")
        while len(durs) > 1 and sum(durs) > config.MAX_DURATION:
            durs.pop(); img_paths.pop(); audio_paths.pop()
            cut = sum(durs)
            all_words = [w for w in all_words if w["start"] < cut]

    print("[2] Subtitr...")
    ass = subtitles.build(all_words, work / "subs.ass")

    print("[2] Ovozlarni birlashtirish...")
    voice = video.concat_audio(audio_paths, work / "voice.m4a")

    print("[2] Video yig'ilmoqda (ffmpeg)...")
    out = work / f"{slug}.mp4"
    video.build(img_paths, durs, voice, ass, out, music=_pick_music())
    thumb = video.thumbnail(out, work / "thumb.jpg", at=min(1.0, durs[0] / 2))

    print(f"[2] Tayyor: {out}  ({sum(durs):.1f}s)")
    return {"video": out, "thumb": thumb, "dir": work, "duration": sum(durs)}
