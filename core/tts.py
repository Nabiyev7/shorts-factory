"""edge-tts — bepul ovoz + so'z-darajasidagi vaqt belgilari.

Microsoft serveri vaqti-vaqti bilan bo'sh javob qaytaradi (NoAudioReceived),
shuning uchun qayta urinish va zaxira ovozlar bor.
"""
import asyncio
import re
import subprocess
import time
import unicodedata
from pathlib import Path

import edge_tts

import config


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def clean(text: str) -> str:
    """edge-tts qoqiladigan belgilarni tozalaydi."""
    t = unicodedata.normalize("NFKC", text)
    t = (t.replace("’", "'").replace("‘", "'")
          .replace("“", '"').replace("”", '"')
          .replace("—", " - ").replace("–", "-")
          .replace("…", "..."))
    # emoji va boshqa belgi-belgilar
    t = "".join(c for c in t if unicodedata.category(c)[0] != "S" or c in "+-=$%")
    t = re.sub(r"\s+", " ", t).strip()
    return t


async def _synth(text: str, out_mp3: Path, voice: str, rate: str, pitch: str):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    words: list[dict] = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,          # 100ns -> sek
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })
    return words


def _voices(primary: str | None) -> list[str]:
    out, seen = [], set()
    for v in [primary or config.VOICE, *config.VOICE_FALLBACKS]:
        v = (v or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def speak(text: str, out_mp3: Path, *, voice: str | None = None,
          rate: str = "+8%", pitch: str = "+0Hz",
          rounds: int = 3) -> tuple[float, list[dict]]:
    """Matnni ovozga aylantiradi. Qaytaradi: (davomiylik_sek, so'zlar)."""
    txt = clean(text)
    if not txt:
        raise RuntimeError("bo'sh matn — ovoz yasab bo'lmaydi")

    voices = _voices(voice)
    last = None

    for rnd in range(rounds):
        for v in voices:
            try:
                words = asyncio.run(_synth(txt, out_mp3, v, rate, pitch))
                if out_mp3.exists() and out_mp3.stat().st_size > 2000 and words:
                    if rnd or v != voices[0]:
                        print(f"    ✓ ovoz {v} bilan chiqdi")
                    return ffprobe_duration(out_mp3), words
                last = RuntimeError("bo'sh audio")
            except Exception as e:  # noqa: BLE001
                last = e
            print(f"    ! tts {v}: {str(last)[:80]}")
            time.sleep(2)
        if rnd < rounds - 1:
            wait = 5 * (rnd + 1)
            print(f"    … tts qayta urinish {rnd + 2}/{rounds}, {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"edge-tts ishlamadi: {last}")


def list_voices(lang_prefix: str = "en") -> None:
    async def _run():
        for v in await edge_tts.list_voices():
            if v["ShortName"].startswith(lang_prefix):
                print(v["ShortName"], "-", v["Gender"], "-", v.get("FriendlyName", ""))
    asyncio.run(_run())


if __name__ == "__main__":
    import sys
    list_voices(sys.argv[1] if len(sys.argv) > 1 else "en")
