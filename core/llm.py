"""Gemini text — JSON qaytaruvchi yordamchi.

Model band bo'lsa (503) yoki limit tugasa (429) — kutadi va boshqa modelga o'tadi.
"""
import json
import random
import time

from google import genai
from google.genai import types

import config

_client = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY .env faylida yo'q")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _models() -> list[str]:
    """Asosiy model + zaxiralar (takrorlanmagan holda)."""
    out, seen = [], set()
    for m in [config.TEXT_MODEL, *config.TEXT_MODEL_FALLBACKS]:
        m = (m or "").strip()
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _retryable(err: Exception) -> bool:
    t = str(err)
    return any(x in t for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                                "500", "INTERNAL", "504", "DEADLINE"))


def json_call(prompt: str, schema: dict, *, temperature: float = 1.0,
              rounds: int = 4) -> dict:
    """Modeldan qat'iy JSON oladi. Har raundda barcha modellar sinab ko'riladi."""
    models = _models()
    last = None

    for rnd in range(rounds):
        for model in models:
            try:
                r = client().models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                if rnd or model != models[0]:
                    print(f"  ✓ {model} bilan ishladi")
                return json.loads(r.text)
            except Exception as e:  # noqa: BLE001
                last = e
                short = str(e)[:120].replace("\n", " ")
                print(f"  ! {model}: {short}")
                if not _retryable(e):
                    # kalit xato / promt xato — boshqa modelda ham shu bo'ladi
                    if "API_KEY" in str(e) or "INVALID_ARGUMENT" in str(e):
                        raise RuntimeError(f"Gemini text ishlamadi: {e}") from None
                time.sleep(1.5)

        wait = min(60, 8 * (2 ** rnd)) + random.uniform(0, 4)
        if rnd < rounds - 1:
            print(f"  … hamma model band, {wait:.0f}s kutilmoqda (raund {rnd + 2}/{rounds})")
            time.sleep(wait)

    raise RuntimeError(f"Gemini text ishlamadi: {last}")
