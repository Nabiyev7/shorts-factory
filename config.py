"""Markaziy konfiguratsiya. Hamma sozlama .env dan o'qiladi."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.resolve()
load_dotenv(ROOT / ".env")


def _b(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "ha")


# --- Google ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TEXT_MODEL = os.getenv("TEXT_MODEL", "gemini-3.5-flash")
# asosiy model band bo'lsa (503) shu ro'yxat bo'ylab o'tadi
TEXT_MODEL_FALLBACKS = [m.strip() for m in os.getenv(
    "TEXT_MODEL_FALLBACKS",
    "gemini-3.6-flash,gemini-2.5-flash,gemini-3.5-flash-lite,gemini-3-flash-preview"
).split(",") if m.strip()]
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3.1-flash-image")  # Nano Banana 2
IMAGE_MODEL_FALLBACK = os.getenv("IMAGE_MODEL_FALLBACK", "gemini-2.5-flash-image")

# --- Rasm provayderi ---
# pollinations = tekin, kalitsiz (FLUX) | gemini = Nano Banana, sifatliroq, pullik
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations").strip().lower()
POLLI_MODEL = os.getenv("POLLI_MODEL", "sana")
IMAGE_SIZE = os.getenv("IMAGE_SIZE", "2K")   # 1K | 2K | 4K (faqat gemini)

# --- Rasm sifatini oshirish (past o'lchamli tekin rasmlar uchun) ---
SHARPEN = float(os.getenv("SHARPEN", "0.9"))      # 0 = o'chirilgan
GRAIN = float(os.getenv("GRAIN", "3"))            # kino donadorligi, 0 = yo'q
VIGNETTE = _b("VIGNETTE", "false")     # quvnoq uslubda kerak emas
SATURATION = float(os.getenv("SATURATION", "1.18"))
BRIGHTNESS = float(os.getenv("BRIGHTNESS", "0.02"))
CONTRAST = float(os.getenv("CONTRAST", "1.04"))
ZOOM_AMP = float(os.getenv("ZOOM_AMP", "0.10"))   # Ken Burns kuchi

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- YouTube ---
YOUTUBE_ENABLED = _b("YOUTUBE_ENABLED", "false")
YOUTUBE_CLIENT_SECRET = ROOT / os.getenv("YOUTUBE_CLIENT_SECRET", "client_secret.json")
YOUTUBE_TOKEN_FILE = ROOT / os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "public")
# CI uchun (fayl o'rniga secret'lar)
YT_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET_VAL = os.getenv("YOUTUBE_CLIENT_SECRET_VALUE", "")
YT_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

# --- Rejim ---
# true bo'lsa: video Telegramga tugmalar bilan boradi, YouTube'ga faqat
# siz "✅ Yukla" ni bosgandan keyin chiqadi.
APPROVAL_MODE = _b("APPROVAL_MODE", "true")

# Promt tayyor bo'lgach botga yuborib, qaror kutish.
# Bu vaqt ichida "O'zim yasayman" bosilmasa — avtomat davom etadi.
HANDOFF = _b("HANDOFF", "true")
HANDOFF_WAIT = int(os.getenv("HANDOFF_WAIT", "120"))   # soniya

# --- Kontent ---
NICHE = os.getenv("NICHE", "mind-blowing history and science facts")
LANG = os.getenv("LANG", "en")
VOICE = os.getenv("VOICE", "en-US-AndrewMultilingualNeural")
SCENES = int(os.getenv("SCENES", "6"))
IMAGE_STYLE = os.getenv(
    "IMAGE_STYLE",
    "bright cinematic photoreal, vivid saturated colours, clean daylight, crisp detail, playful",
)

# Umumiy kayfiyat — Agent 1 promtlarni shu ruhda yozadi
MOOD = os.getenv("MOOD", "").strip() or (
    "Bright, colourful, cheerful and full of wonder. Sunny daylight or vivid colourful "
    "light, saturated happy colours, clean crisp air, lively energy. It should feel like "
    "a fun popular-science channel, never like a horror film."
)

# --- Video ---
W, H, FPS = 1080, 1920, 30
XFADE = 0.4          # sahnalar orasidagi o'tish (sek)
MAX_DURATION = 59.0  # Shorts limiti

# --- Yo'llar ---
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "state"
MUSIC_DIR = ROOT / os.getenv("MUSIC_DIR", "assets/music")
MUSIC_VOLUME = float(os.getenv("MUSIC_VOLUME", "0.10"))

for _d in (OUTPUT_DIR, STATE_DIR, MUSIC_DIR):
    _d.mkdir(parents=True, exist_ok=True)
