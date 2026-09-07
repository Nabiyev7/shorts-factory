"""ffmpeg: rasm + Ken Burns + o'tish + ovoz + subtitr + musiqa -> Shorts mp4."""
import random
import shlex
import subprocess
from pathlib import Path

import config


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg xato:\n{' '.join(shlex.quote(c) for c in cmd)}\n\n{p.stderr[-3000:]}")


def concat_audio(parts: list[Path], out: Path) -> Path:
    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", str(p)]
    n = len(parts)
    cmd += [
        "-filter_complex", f"{''.join(f'[{i}:a]' for i in range(n))}concat=n={n}:v=0:a=1[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out),
    ]
    run(cmd)
    return out


def _kenburns(idx: int, dur: float, zoom_in: bool) -> str:
    """Bitta rasm uchun filtr zanjiri: sifatli upscale + o'tkirlash + Ken Burns."""
    frames = max(2, int(round(dur * config.FPS)))
    amp = config.ZOOM_AMP
    step = amp / frames
    if zoom_in:
        z = f"min(1+{step:.6f}*on,{1 + amp:.3f})"
    else:
        z = f"max({1 + amp:.3f}-{step:.6f}*on,1.0)"
    drift = random.choice(["-", "+"])
    x = f"iw/2-(iw/zoom/2){drift}(on/{frames})*30"

    # zoom uchun zaxira: chiqish o'lchamining 1.25 barobari
    W2, H2 = int(config.W * 1.25), int(config.H * 1.25)
    chain = [
        f"[{idx}:v]scale={W2}:{H2}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={W2}:{H2}",
    ]
    if config.SHARPEN > 0:
        chain.append(f"unsharp=5:5:{config.SHARPEN:.2f}:5:5:0.0")
    chain += [
        f"zoompan=z='{z}':d=1:x='{x}':y='ih/2-(ih/zoom/2)':s={config.W}x{config.H}:fps={config.FPS}",
        "setsar=1",
        "format=yuv420p",
    ]
    return ",".join(chain) + f"[v{idx}]"


def build(images: list[Path], durations: list[float], voice: Path,
          ass: Path, out: Path, music: Path | None = None) -> Path:
    """durations[i] = i-sahna ovozining uzunligi (sek)."""
    assert len(images) == len(durations)
    n = len(images)
    xf = config.XFADE

    cmd = ["ffmpeg", "-y"]
    for i, img in enumerate(images):
        cmd += ["-loop", "1", "-framerate", str(config.FPS),
                "-t", f"{durations[i] + xf:.3f}", "-i", str(img)]
    voice_idx = n
    cmd += ["-i", str(voice)]
    music_idx = None
    if music:
        music_idx = n + 1
        cmd += ["-stream_loop", "-1", "-i", str(music)]

    filters = [_kenburns(i, durations[i] + xf, i % 2 == 0) for i in range(n)]

    # xfade zanjiri
    if n == 1:
        vlabel = "v0"
    else:
        acc = durations[0]
        prev = "v0"
        for i in range(1, n):
            lbl = f"x{i}"
            filters.append(
                f"[{prev}][v{i}]xfade=transition={'fade' if i % 2 else 'smoothleft'}:"
                f"duration={xf}:offset={acc:.3f}[{lbl}]"
            )
            acc += durations[i]
            prev = lbl
        vlabel = prev

    total = sum(durations) + xf

    grade = [f"eq=saturation={config.SATURATION}:brightness={config.BRIGHTNESS}"
             f":contrast={config.CONTRAST}"]
    if config.GRAIN > 0:
        grade.append(f"noise=alls={int(config.GRAIN)}:allf=t+u")
    if config.VIGNETTE:
        grade.append("vignette=PI/6")
    if grade:
        filters.append(f"[{vlabel}]" + ",".join(grade) + "[vg]")
        vlabel = "vg"

    ass_path = str(ass).replace("\\", "/").replace(":", r"\:")
    filters.append(f"[{vlabel}]subtitles='{ass_path}'[vout]")

    if music_idx is not None:
        filters.append(
            f"[{music_idx}:a]volume={config.MUSIC_VOLUME},afade=t=out:st={total - 1.5:.2f}:d=1.5[m]"
        )
        filters.append(f"[{voice_idx}:a][m]amix=inputs=2:duration=first:dropout_transition=0[aout]")
    else:
        filters.append(f"[{voice_idx}:a]anull[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(config.FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    return out


def thumbnail(video: Path, out: Path, at: float = 1.0) -> Path:
    run(["ffmpeg", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1",
         "-q:v", "2", str(out)])
    return out


# ---------------- tayyor kliplardan yig'ish (Google Flow / Veo / Kling) ----------------
def _clip_filter(idx: int, dur: float) -> str:
    """Bitta klipni 1080x1920 ga solib, kerakli uzunlikka keltiradi.

    Qisqa bo'lsa oxirgi kadr ushlab turiladi, uzun bo'lsa kesiladi.
    Klipning o'z ovozi olib tashlanadi (biz TTS ishlatamiz).
    """
    return (
        f"[{idx}:v]scale={config.W}:{config.H}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={config.W}:{config.H},fps={config.FPS},"
        f"tpad=stop_mode=clone:stop_duration={dur:.3f},"
        f"trim=duration={dur:.3f},setpts=PTS-STARTPTS,"
        f"setsar=1,format=yuv420p[v{idx}]"
    )


def build_from_clips(clips: list[Path], durations: list[float], voice: Path,
                     ass: Path, out: Path, music: Path | None = None) -> Path:
    """Har sahnaga bitta video klip: kliplar + TTS ovoz + subtitr -> Shorts mp4."""
    assert len(clips) == len(durations)
    n = len(clips)
    xf = config.XFADE

    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", str(c)]
    voice_idx = n
    cmd += ["-i", str(voice)]
    music_idx = None
    if music:
        music_idx = n + 1
        cmd += ["-stream_loop", "-1", "-i", str(music)]

    filters = [_clip_filter(i, durations[i] + xf) for i in range(n)]

    if n == 1:
        vlabel = "v0"
    else:
        acc = durations[0]
        prev = "v0"
        for i in range(1, n):
            lbl = f"x{i}"
            filters.append(
                f"[{prev}][v{i}]xfade=transition=fade:duration={xf}:offset={acc:.3f}[{lbl}]"
            )
            acc += durations[i]
            prev = lbl
        vlabel = prev

    total = sum(durations) + xf

    grade = [f"eq=saturation={config.SATURATION}:brightness={config.BRIGHTNESS}"
             f":contrast={config.CONTRAST}"]
    if config.VIGNETTE:
        grade.append("vignette=PI/6")
    filters.append(f"[{vlabel}]" + ",".join(grade) + "[vg]")
    vlabel = "vg"

    ass_path = str(ass).replace("\\", "/").replace(":", r"\:")
    filters.append(f"[{vlabel}]subtitles='{ass_path}'[vout]")

    if music_idx is not None:
        filters.append(
            f"[{music_idx}:a]volume={config.MUSIC_VOLUME},afade=t=out:st={total - 1.5:.2f}:d=1.5[m]")
        filters.append(f"[{voice_idx}:a][m]amix=inputs=2:duration=first:dropout_transition=0[aout]")
    else:
        filters.append(f"[{voice_idx}:a]anull[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(config.FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    return out
