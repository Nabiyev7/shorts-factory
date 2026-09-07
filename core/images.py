"""Rasm generatsiya — ikki provayder:

  IMAGE_PROVIDER=gemini         Nano Banana 2 (gemini-3.1-flash-image) — sifatli, pullik
  IMAGE_PROVIDER=pollinations   tekin, kalit kerak emas (FLUX)

Biri ishlamasa ikkinchisiga o'zi o'tadi.
"""
import random
import time
import urllib.parse
from pathlib import Path

import requests

import config

POLLI = "https://image.pollinations.ai/prompt/{p}"

NEGATIVE = ("no text, no letters, no numbers, no captions, no subtitles, no watermark, "
            "no logo, no signage, no borders, no frames, no split screen, no collage, "
            "not dark, not gloomy, no fog, no haze, no smoke, no blood, no gore, "
            "no corpses, no decay, no horror, not creepy, not eerie, not desaturated, "
            "not muted, not monochrome, not sepia")


def build_prompt(scene: dict, style: dict | None) -> str:
    """Sahna promti + umumiy uslub kitobi -> modelga beriladigan yakuniy matn."""
    style = style or {}
    p0 = scene.get("image_prompt", "").strip()
    parts = [p0 if p0.endswith(".") else p0 + "."]

    shot = scene.get("shot", "").strip()
    if shot:
        parts.append(f"Camera: {shot}.")

    bits = [style.get(k, "").strip() for k in
            ("look", "palette", "lighting", "era_setting", "subject_sheet")]
    bits = [b for b in bits if b]
    if bits:
        parts.append("Visual style (must match exactly): " + " | ".join(bits) + ".")
    elif config.IMAGE_STYLE:
        parts.append(f"Visual style: {config.IMAGE_STYLE}.")

    parts.append("Vertical 9:16 composition, subject in the upper two-thirds, "
                 "lower third visually calm and uncluttered. "
                 "Bright, colourful, cheerful, well-lit, high saturation.")
    parts.append(NEGATIVE + ".")
    return " ".join(parts)


# ---------------- tekin: Pollinations ----------------
def _pollinations(prompt: str, out: Path, retries: int = 4) -> Path:
    q = urllib.parse.quote(prompt[:1800], safe="")
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(
                POLLI.format(p=q),
                params={"width": 1080, "height": 1920, "model": config.POLLI_MODEL,
                        "nologo": "true", "private": "true", "enhance": "false",
                        "seed": random.randint(1, 10**9)},
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
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            image_size=config.IMAGE_SIZE,
                        ),
                    ),
                )
                data = _extract(resp)
                if data:
                    out.write_bytes(data)
                    return out
                last = RuntimeError("javobda rasm yo'q (moderatsiya?)")
            except Exception as e:  # noqa: BLE001
                last = e
            print(f"  ! {model} urinish {attempt + 1}: {last}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gemini rasm chiqmadi: {last}")


# ---------------- umumiy ----------------
def generate(scene: dict | str, out_path: Path, style: dict | None = None) -> Path:
    prompt = build_prompt(scene, style) if isinstance(scene, dict) else str(scene)
    order = ([_gemini, _pollinations] if config.IMAGE_PROVIDER == "gemini"
             else [_pollinations, _gemini])
    last = None
    for fn in order:
        try:
            return fn(prompt, out_path)
        except Exception as e:  # noqa: BLE001
            last = e
            print("  → boshqa provayderga o'tilmoqda…")
    raise RuntimeError(f"rasm chiqmadi: {last}")
