"""Orkestrator: Agent 1 -> Agent 2 -> Agent 3.

Misollar:
    python run.py                 # to'liq: g'oya + video + publish
    python run.py --count 3       # 3 ta video ketma-ket
    python run.py --no-publish    # faqat video yasaydi
    python run.py --idea-only     # faqat g'oya/skriptni ko'rsatadi
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402
from agents import handoff, idea_agent, publish_agent, render_agent  # noqa: E402
from core import state  # noqa: E402


def one(publish: bool = True, scenes: int | None = None) -> dict:
    idea = idea_agent.run(scenes)

    if config.HANDOFF:
        work = config.OUTPUT_DIR / "handoff_tmp"
        work.mkdir(parents=True, exist_ok=True)
        decision = handoff.ask(idea, work)
        if decision["mode"] == "mine":
            state.add({"title": idea["youtube_title"], "topic": idea["topic"],
                       "uid": decision["uid"], "status": "handoff"})
            return {"idea": idea, "handoff": True, "uid": decision["uid"],
                    "video": None, "dir": work, "duration": 0}

    assets = render_agent.run(idea)
    (assets["dir"] / "idea.json").write_text(
        json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {}
    if publish:
        result = publish_agent.run(assets, idea)

    if not result.get("pending"):
        state.add({
            "title": idea["youtube_title"],
            "topic": idea["topic"],
            "video": str(assets["video"]),
            "duration": round(assets["duration"], 1),
            "youtube_id": result.get("youtube_id"),
        })
    else:
        # tasdiq kutilmoqda — mavzu takrorlanmasligi uchun tarixga darhol yozamiz
        state.add({"title": idea["youtube_title"], "topic": idea["topic"],
                   "uid": result["uid"], "status": "pending"})

    out = {"idea": idea, **assets, **result}
    _emit_ci_outputs(out)
    return out


def _emit_ci_outputs(r: dict) -> None:
    """GitHub Actions uchun: artifact nomi va yo'llar."""
    gh_out = os.getenv("GITHUB_OUTPUT")
    if not gh_out:
        return
    uid = r.get("uid", "")
    with open(gh_out, "a", encoding="utf-8") as f:
        if r.get("handoff") or not r.get("video"):
            f.write("uid=\n")
            return
        f.write(f"uid={uid}\n")
        f.write(f"artifact=short-{uid}\n")
        f.write(f"dir={r['dir']}\n")
        f.write(f"video={r['video']}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--scenes", type=int, default=None)
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--idea-only", action="store_true")
    a = ap.parse_args()

    if a.idea_only:
        print(json.dumps(idea_agent.run(a.scenes), ensure_ascii=False, indent=2))
        return

    ok = 0
    for i in range(a.count):
        print(f"\n{'=' * 46}\n  VIDEO {i + 1}/{a.count}\n{'=' * 46}")
        try:
            r = one(publish=not a.no_publish, scenes=a.scenes)
            if r.get("handoff"):
                print("\n⏸ Sizning rasmlaringiz kutilmoqda (botga tashlang)")
            else:
                print(f"\n✅ {r['video']}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            print("❌ Bu video o'tkazib yuborildi, keyingisiga o'tildi")
            try:                       # xatodan xabar bering
                from core import telegram
                telegram.send_message(
                    f"❌ <b>Video yasalmadi</b>\n<code>{str(e)[:400]}</code>")
            except Exception:  # noqa: BLE001
                pass
    print(f"\nYakun: {ok}/{a.count} tayyor. Papka: {config.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
