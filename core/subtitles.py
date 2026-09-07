"""So'z-darajasidagi 'pop-up' ASS subtitr (Shorts uslubi)."""
from pathlib import Path

import config

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

HILITE = r"{\c&H00E5FF&}"   # BGR: sariq-oltin
NORMAL = r"{\c&HFFFFFF&}"


def _ts(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build(words: list[dict], out_path: Path, *, group: int = 3,
          font: str = "DejaVu Sans", size: int = 96) -> Path:
    """words: [{text,start,end}] global vaqtda. Har 'group' so'z bitta qatorda,
    aytilayotgan so'z sariq rangda va biroz kattalashadi."""
    lines = [HEADER.format(w=config.W, h=config.H, font=font, size=size)]

    for i in range(0, len(words), group):
        chunk = words[i:i + group]
        for j, wd in enumerate(chunk):
            start = wd["start"]
            end = chunk[j + 1]["start"] if j + 1 < len(chunk) else wd["end"] + 0.06
            if end <= start:
                end = start + 0.12
            parts = []
            for k, other in enumerate(chunk):
                txt = other["text"].replace("{", "").replace("}", "")
                if k == j:
                    parts.append(HILITE + r"{\fscx112\fscy112}" + txt + r"{\fscx100\fscy100}")
                else:
                    parts.append(NORMAL + txt)
            text = " ".join(parts)
            fx = r"{\fad(60,60)}" if j == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{fx}{text}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
