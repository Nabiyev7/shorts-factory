"""Gemini text — JSON qaytaruvchi yordamchi."""
import json
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


def json_call(prompt: str, schema: dict, *, temperature: float = 1.0, retries: int = 3) -> dict:
    """Modeldan qat'iy JSON oladi (response_schema bilan)."""
    last = None
    for attempt in range(retries):
        try:
            r = client().models.generate_content(
                model=config.TEXT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(r.text)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  ! llm urinish {attempt + 1}/{retries} xato: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Gemini text ishlamadi: {last}")
