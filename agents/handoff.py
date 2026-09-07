"""Promtni Telegramga yuborib, 2 daqiqa qaror kutish.

Oqim:
    Agent 1 promt yozdi
        -> botga skript + rasm promtlari boradi
        -> [🎨 O'zim yasayman]  [🤖 Hozir yasa]
        -> HANDOFF_WAIT (standart 120 s) ichida hech narsa bosilmasa -> avtomat davom etadi
        -> "O'zim yasayman" bosilsa -> ish `state/handoff/` ga yoziladi va to'xtaydi;
           siz rasmlarni (yoki tayyor videoni) botga tashlaysiz, approve.py yig'adi.
"""
import json
import time
import uuid

import config
from core import telegram, updates

HANDOFF_DIR = config.STATE_DIR / "handoff"
HANDOFF_DIR.mkdir(parents=True, exist_ok=True)


def prompts_text(idea: dict) -> str:
    sb = idea.get("style_bible", {})
    out = [f"# {idea['topic']}", "", f"TITLE: {idea['youtube_title']}", "",
           "## UMUMIY USLUB (hamma rasmga qo'shing)"]
    for k in ("look", "palette", "lighting", "era_setting", "subject_sheet"):
        if sb.get(k):
            out.append(f"- {k}: {sb[k]}")
    out.append("")
    for i, sc in enumerate(idea["scenes"], 1):
        out += [f"{'=' * 60}",
                f"## SAHNA {i}",
                f"{'=' * 60}",
                f"MATN:  {sc['narration']}",
                f"KADR:  {sc.get('shot', '')}",
                "",
                "--- RASM PROMTI (Nano Banana / Midjourney / Flux) ---",
                sc["image_prompt"],
                "",
                "--- VIDEO PROMTI (Veo / Kling / Runway / Sora) ---",
                sc.get("video_prompt", "(yo'q)"),
                ""]
    n = len(idea["scenes"])
    out += [f"{'=' * 60}",
            "## QANDAY YUBORASIZ (uchta yo'l)",
            "",
            f"1) RASM yo'li — {n} ta rasmni SAHNA TARTIBIDA yuboring.",
            "   Ovoz, subtitr va montajni men qo'shaman.",
            "   Sifat uchun Telegram'da 'File' sifatida yuboring.",
            "",
            f"2) KLIP yo'li (Google Flow / Veo / Kling) — {n} ta klipni tartibda yuboring.",
            "   Flow'da: yangi loyiha -> Text to Video -> nisbatni 9:16 qiling ->",
            "   yuqoridagi VIDEO PROMTI ni qo'ying -> klipni yuklab oling.",
            "   Klipning o'z ovozi tashlab yuboriladi, biz TTS ishlatamiz.",
            "   Har klip ~8 soniya bo'lsa yetarli — men sahna uzunligiga moslayman.",
            "",
            "3) TAYYOR VIDEO — 20 soniyadan uzun bitta video yuborsangiz,",
            "   montaj o'tkazib yuborilib, to'g'ridan-to'g'ri YouTube uchun tayyorlanadi.",
            "",
            f"{'=' * 60}",
            "## ESLATMA",
            "- 9:16 vertikal, pastki uchdan bir qismi bo'sh (subtitr o'sha yerda)",
            "- Telegram cheklovi: har fayl 20 MB dan kichik bo'lsin",
            "- Yetmagan bo'lsa ham 'Videoni yig'' tugmasi bilan yig'dirsangiz bo'ladi"]
    return "\n".join(out)


def _short(idea: dict) -> str:
    sc = idea["scenes"]
    lines = [f"📝 <b>{idea['youtube_title']}</b>", ""]
    for i, s in enumerate(sc, 1):
        lines.append(f"<b>{i}.</b> {s['narration']}")
    lines += ["", f"⏱ {config.HANDOFF_WAIT} soniya ichida tanlamasangiz — o'zi yasayveradi."]
    return "\n".join(lines)


def ask(idea: dict, workdir) -> dict:
    """Promtni yuboradi va qarorni kutadi. {'mode': 'auto'|'mine', 'uid': ...}"""
    uid = uuid.uuid4().hex[:10]

    txt = workdir / "prompts.txt"
    txt.write_text(prompts_text(idea), encoding="utf-8")

    msg = telegram.send_message(_short(idea))
    telegram.send_document(txt, "📎 To'liq promtlar", telegram.handoff_keyboard(uid))
    print(f"[1.5] Promt botga yuborildi, {config.HANDOFF_WAIT}s kutilmoqda (uid={uid})")

    deadline = time.time() + config.HANDOFF_WAIT
    while time.time() < deadline:
        time.sleep(5)
        updates.fetch()
        for u, action, u_uid in updates.callbacks(("mine", "auto")):
            if u_uid != uid:
                continue
            updates.drop([u["update_id"]])
            cq = u["callback_query"]
            if action == "auto":
                telegram.answer_callback(cq["id"], "Yasashni boshladim")
                print("[1.5] 'Hozir yasa' bosildi")
                return {"mode": "auto", "uid": uid}

            telegram.answer_callback(cq["id"], "Rasmlarni yuboring")
            job = {
                "uid": uid,
                "idea": idea,
                "created": int(time.time()),
                "message_id": msg["message_id"],
                "need": len(idea["scenes"]),
            }
            (HANDOFF_DIR / f"{uid}.json").write_text(
                json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
            telegram.send_message(
                f"🎨 Yaxshi — {len(idea['scenes'])} ta rasmni sahna tartibida shu yerga "
                f"tashlang (sifat uchun <b>File</b> sifatida).\n"
                f"Hammasi kelgach o'zim videoni yig'aman.\n\n"
                f"Yoki tayyor videoni yuborsangiz — to'g'ridan-to'g'ri YouTube uchun tayyorlayman."
            )
            print("[1.5] 'O'zim yasayman' bosildi — ish kutish rejimiga o'tdi")
            return {"mode": "mine", "uid": uid}

    print("[1.5] Javob bo'lmadi — avtomat davom etilmoqda")
    telegram.send_message("⏱ Javob bo'lmadi — o'zim yasayapman…")
    return {"mode": "auto", "uid": uid}
