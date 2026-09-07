"""AGENT 1 — g'oya topadi, tahlil qiladi, skript + kinematik rasm promtlarini yozadi."""
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
        "style_bible": {
            "type": "object",
            "description": "Barcha sahnalarga umumiy vizual DNK",
            "properties": {
                "look": {"type": "string"},
                "palette": {"type": "string"},
                "lighting": {"type": "string"},
                "era_setting": {"type": "string"},
                "subject_sheet": {"type": "string"},
            },
            "required": ["look", "palette", "lighting", "era_setting", "subject_sheet"],
        },
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "video_prompt": {"type": "string"},
                    "shot": {"type": "string"},
                },
                "required": ["narration", "image_prompt", "video_prompt", "shot"],
            },
        },
    },
    "required": ["topic", "why_it_works", "youtube_title", "youtube_description",
                 "tags", "slug", "style_bible", "scenes"],
}

PROMPT = """You are a top-performing YouTube Shorts writer AND a film director who writes
image prompts for a state-of-the-art text-to-image model. Niche: {niche}.

Produce ONE new short: {scenes} scenes, ~35-50 seconds of spoken narration.

ALREADY USED — do not repeat these or anything close:
{used}

=========================  SCRIPT  =========================
- Language: {lang}. Spoken English, simple words, present tense, punchy.
- Scene 1 is the HOOK: max 12 words. Instant curiosity or shock. Never "did you know".
- Scenes 2..n-1: 12-22 words each, one idea, rising tension.
- Last scene: satisfying kicker + soft CTA ("follow for more").
- Every claim must be FACTUALLY TRUE and verifiable. No invented numbers.
- Pick a topic that makes people smile or say "no way!" — wonder, curiosity, clever
  tricks, funny accidents, weird animals, surprising inventions.
  Avoid plagues, massacres, torture, executions, disasters and disease.

=====================  VISUAL DIRECTION  ====================
First write a `style_bible` — the visual DNA every scene must obey:
  look          one sentence: medium + rendering (e.g. "bright 35mm cinema still, clean
                Kodak Ektar colour, crisp detail, playful, photoreal")
  palette       3-4 bright, saturated colours (e.g. "sunflower yellow, sky blue,
                coral pink, fresh mint" — cheerful and high-chroma, never muddy)
  lighting      one dominant scheme, always BRIGHT (e.g. "golden hour sun, soft bounce,
                clear air" / "midday daylight, crisp shadows" / "colourful studio lights")
  era_setting   period, place, architecture, clothing, materials
  subject_sheet if a person/creature recurs: fixed age, build, hair, clothing, distinguishing
                marks — SAME words reused every scene so the character stays consistent.
                If no recurring subject, describe the recurring PLACE instead.

Then, for each scene:
  shot          camera language only: e.g. "extreme close-up, 85mm, eye level, shallow focus"
                Vary it across scenes — wide establishing / medium / close-up / macro /
                over-the-shoulder / low-angle hero / top-down. Never two identical shots in a row.
  image_prompt  50-90 words, ONE continuous sentence-flow, in this order:
                  1. subject + exactly what it is DOING (a verb, mid-action, not a pose)
                  2. environment and 2-3 concrete physical details (texture, weather, props)
                  3. light: direction, quality, colour temperature
                  4. camera: lens, angle, depth of field, motion blur if any
                  5. mood + colour grade, echoing the palette
                Write it so the picture would be striking even with the sound off.
                Restate the key style_bible words inside every prompt — the model has no memory.
  video_prompt  40-70 words for a TEXT-TO-VIDEO model (Veo / Kling / Runway / Sora).
                SAME subject, same environment, same style_bible words as image_prompt —
                it must look like the same film. Differences:
                  - describe MOTION over ~5-8 seconds: what the subject does from start to end
                  - describe CAMERA MOVEMENT: slow push-in, handheld drift, orbit, tilt up,
                    static locked-off — pick one, name it explicitly
                  - describe what moves in the environment: smoke, rain, dust, cloth, crowd
                  - one continuous take, no cuts, no transitions, no montage
                  - end with: "no text, no subtitles, no watermark"

=====================  MOOD (VERY IMPORTANT)  ====================
{mood}

BANNED in every prompt — these make it look like horror, which is wrong:
  darkness, gloom, shadowy figures, silhouettes in the dark, fog, mist, haze,
  smoke, blood, gore, corpses, decay, rot, ruins, rust, cracked skin, screaming
  faces, empty staring eyes, grimdark, desaturated, washed-out, muted, sepia,
  monochrome, teal-and-orange, dystopian, eerie, ominous, sinister, creepy.
Do not describe anyone as frightened, suffering, dying or in pain.
If the topic itself is grim, show the WONDER and the CURIOSITY in it instead —
the discovery, the colourful detail, the amazed face — never the horror.

HARD RULES for BOTH image_prompt and video_prompt:
- Vertical 9:16 framing; leave the lower third visually calm (subtitles sit there).
- NEVER request text, letters, numbers, captions, signage, logos, watermarks or UI.
- No real living public figures, no brand names, no copyrighted characters.
- Concrete nouns and verbs only — no "beautiful", "amazing", "epic", "masterpiece", "8k".
- Colour must be explicit and vivid in EVERY prompt: name at least two bright colours.
- Light must be explicit and bright in EVERY prompt.
- No collages, no split screens, no borders, no frames.

=========================  META  ===========================
- youtube_title: under 60 chars, real curiosity gap, no lies. End with #Shorts.
- youtube_description: 2 short lines + 5 hashtags.
- tags: 12 lowercase YouTube tags.
- slug: short kebab-case ascii filename.

Return JSON only."""


def run(scenes: int | None = None) -> dict:
    scenes = scenes or config.SCENES
    used = "\n".join(f"- {t}" for t in state.titles()) or "- (bo'sh)"
    idea = llm.json_call(
        PROMPT.format(niche=config.NICHE, scenes=scenes, lang=config.LANG,
                      used=used, mood=config.MOOD),
        SCHEMA,
        temperature=1.15,
    )
    idea["scenes"] = idea["scenes"][:scenes]
    sb = idea.get("style_bible", {})
    print(f"[1] G'oya: {idea['topic']}")
    print(f"    Sarlavha: {idea['youtube_title']}")
    print(f"    Uslub: {sb.get('look', '?')[:70]}")
    print(f"    Sahnalar: {len(idea['scenes'])}")
    return idea


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
