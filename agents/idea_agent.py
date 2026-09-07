"""AGENT 1 — g'oya topadi, tahlil qiladi, skript + rasm promtlarini yozadi."""
import json

import config
from core import llm, state

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "why_it_works": {"type": "string"},
        "youtube_title": {"type": "string"},
        "youtube_description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "slug": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["narration", "image_prompt"],
            },
        },
    },
    "required": ["topic", "why_it_works", "youtube_title", "youtube_description",
                 "tags", "slug", "scenes"],
}

PROMPT = """You are a top-performing YouTube Shorts writer. Niche: {niche}.

Produce ONE new short (about 35-50 seconds of spoken narration, {scenes} scenes).

ALREADY USED — do not repeat these or anything close to them:
{used}

Rules:
- Language: {lang}. Narration must be spoken English, simple words, present tense, punchy.
- Scene 1 is the HOOK: max 12 words, must create instant curiosity or shock. No "did you know".
- Each following scene: 12-22 words, one idea, builds tension, ends on a payoff.
- Last scene: a satisfying kicker + a soft call to action ("follow for more").
- Everything must be FACTUALLY TRUE and verifiable. No made-up numbers.
- image_prompt: a self-contained visual description for a text-to-image model.
  Describe subject, action, camera angle, lighting, mood. Vertical framing.
  NEVER ask for text, letters, captions, logos or watermarks in the image.
  Keep visual continuity across scenes (same era, palette, subject).
- youtube_title: under 60 chars, curiosity gap, no clickbait lies. Add #Shorts at the end.
- youtube_description: 2 short lines + 5 hashtags.
- tags: 12 lowercase YouTube tags.
- slug: short kebab-case file name, ascii only.

Return JSON only."""


def run(scenes: int | None = None) -> dict:
    scenes = scenes or config.SCENES
    used = "\n".join(f"- {t}" for t in state.titles()) or "- (bo'sh)"
    idea = llm.json_call(
        PROMPT.format(niche=config.NICHE, scenes=scenes, lang=config.LANG, used=used),
        SCHEMA,
        temperature=1.15,
    )
    idea["scenes"] = idea["scenes"][:scenes]
    print(f"[1] G'oya: {idea['topic']}")
    print(f"    Sarlavha: {idea['youtube_title']}")
    print(f"    Sahnalar: {len(idea['scenes'])}")
    return idea


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
