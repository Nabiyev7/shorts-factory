"""Tarix: qaysi mavzular ishlatilgani — takrorlanmaslik uchun."""
import json
from datetime import datetime
from config import STATE_DIR

HISTORY = STATE_DIR / "history.json"


def load() -> list[dict]:
    if HISTORY.exists():
        try:
            return json.loads(HISTORY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def titles(limit: int = 80) -> list[str]:
    return [x.get("title", "") for x in load()][-limit:]


def add(entry: dict) -> None:
    data = load()
    entry["created_at"] = datetime.now().isoformat(timespec="seconds")
    data.append(entry)
    HISTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
