"""edge-tts — bepul ovoz + so'z-darajasidagi vaqt belgilari."""
import asyncio
import subprocess
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


def speak(text: str, out_mp3: Path, *, voice: str | None = None,
          rate: str = "+8%", pitch: str = "+0Hz") -> tuple[float, list[dict]]:
    """Matnni ovozga aylantiradi. Qaytaradi: (davomiylik_sek, so'zlar)."""
    voice = voice or config.VOICE
    words = asyncio.run(_synth(text, out_mp3, voice, rate, pitch))
    return ffprobe_duration(out_mp3), words


def list_voices(lang_prefix: str = "en") -> None:
    async def _run():
        for v in await edge_tts.list_voices():
            if v["ShortName"].startswith(lang_prefix):
                print(v["ShortName"], "-", v["Gender"], "-", v.get("FriendlyName", ""))
    asyncio.run(_run())


if __name__ == "__main__":
    import sys
    list_voices(sys.argv[1] if len(sys.argv) > 1 else "en")
