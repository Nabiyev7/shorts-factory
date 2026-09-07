"""Rasm generatsiya — ikki provayder:

  IMAGE_PROVIDER=pollinations   tekin, kalit kerak emas (FLUX)
  IMAGE_PROVIDER=gemini         Nano Banana, sifatliroq, pullik (~$0.03/rasm)

Biri ishlamasa ikkinchisiga o'zi o'tadi.
"""
import random
import time
import urllib.parse
from pathlib import Path

import requests

import config

POLLI = "https://image.pollinations.ai/prompt/{p}"


def _full_prompt(prompt: str) -> str:
    return (f"{prompt}. {config.IMAGE_STYLE}. "
            f"Vertical 9:16 composition. No text, no letters, no watermark, no logo.")


# ---------------- tekin: Pollinations ----------------
def _pollinations(prompt: str, out: Path, retries: int = 4) -> Path:
    q = urllib.parse.quote(_full_prompt(prompt)[:1500], safe="")
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(
                POLLI.format(p=q),
                params={
                    "width": 896, "height": 1600,
                    "model": config.POLLI_MODEL,
                    "nologo": "true", "private": "true", "enhance": "true",
                    "seed": random.randint(1, 10**9),
                },
                timeout=180,
            )
            r.raise_for_status()
            if not r.headers.get("content-type", "").startswith("image"):
                raise RuntimeError(f"rasm emas: {r.headers.get('content-type')}")
            if len(r.content) < 20_000:
                raise RuntimeError("rasm juda kichik / bo'sh")
            out.write_bytes(r.content)
            return out
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  ! pollinations urinish {attempt + 1}/{retries}: {e}")
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"pollinations ishlamadi: {last}")


# ---------------- pullik: Nano Banana ----------------
def _extract(resp) -> bytes | None:
    for cand in getattr(resp, "candidates", []) or []:
        for part in getattr(cand.content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return inline.data
    return None


def _gemini(prompt: str, out: Path, retries: int = 3) -> Path:
    from google.genai import types

    from core.llm import client

    last = None
    for model in (config.IMAGE_MODEL, config.IMAGE_MODEL_FALLBACK):
        for attempt in range(retries):
            try:
                resp = client().models.generate_content(
                    model=model,
                    contents=_full_prompt(prompt),
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="9:16", image_size="2K"),
                    ),
                )
                data = _extract(resp)
                if data:
                    out.write_bytes(data)
                    return out
                last = RuntimeError("javobda rasm yo'q (moderatsiya?)")
            except Exception as e:  # noqa: BLE001
                last = e
            print(f"  ! nano-banana urinish {attempt + 1} ({model}): {last}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"nano banana ishlamadi: {last}")


# ---------------- umumiy ----------------
def generate(prompt: str, out_path: Path) -> Path:
    order = ([_pollinations, _gemini] if config.IMAGE_PROVIDER == "pollinations"
             else [_gemini, _pollinations])
    last = None
    for fn in order:
        try:
            return fn(prompt, out_path)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  → boshqa provayderga o'tilmoqda…")
    raise RuntimeError(f"rasm chiqmadi: {last}")
