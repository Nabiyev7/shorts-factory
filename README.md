# Shorts Factory — 3 agentli YouTube Shorts konveyeri

```
Agent 1  g'oya + tahlil + skript + rasm promtlari   (Gemini text)
   ↓
Agent 2  rasm (Nano Banana) + ovoz (edge-tts) + subtitr + ffmpeg  → .mp4
   ↓
Agent 3  Telegram botga tashlaydi + YouTube'ga yuklaydi
```

Bitta buyruq — tayyor video kanalda va Telegramda.

---

## 1. Nima kerak

### 💸 To'liq tekin rejim (standart)

`.env` da `IMAGE_PROVIDER=pollinations` bo'lsa **hech qanday to'lov yo'q**:

| Bo'lak | Nima ishlatiladi | Narx |
|---|---|---|
| Skript / g'oya | Gemini **free tier** (kuniga 2 ta so'rov — limitdan juda pastda) | $0 |
| Rasmlar | Pollinations (FLUX), kalit kerak emas | $0 |
| Ovoz | edge-tts | $0 |
| Server | GitHub Actions, public repo → cheksiz daqiqa | $0 |
| Telegram + YouTube | API'lari tekin | $0 |

Sifat muhimroq bo'lsa `IMAGE_PROVIDER=gemini` qiling — Nano Banana chiroyliroq
chiqaradi, lekin ~$0.03/rasm (1 video ≈ $0.20). Biri ishlamay qolsa kod
avtomat ikkinchisiga o'tadi.

---

| Narsa | Qayerdan | Narx |
|---|---|---|
| **Gemini API key** | https://aistudio.google.com/apikey — **free tier yetarli** | $0 (yoki rasm uchun ~$0.03/dona) |
| **Telegram bot token** | Telegramda `@BotFather` → `/newbot` | tekin |
| **Telegram kanal ID** | Kanal yarating, botni **admin** qiling, `@username` yozing | tekin |
| **YouTube OAuth** (ixtiyoriy) | Google Cloud Console → YouTube Data API v3 → OAuth client (Desktop) | tekin |
| **GitHub token** | https://github.com/settings/tokens/new (scopes: `repo` + `workflow`) | tekin |
| **git** | https://git-scm.com/download/win | tekin |
| **ffmpeg** | https://ffmpeg.org/download.html (lokal ishlatsangiz) | tekin |
| **Python 3.10+** | python.org | tekin |
| Ovoz (TTS) | edge-tts — kalit kerak emas | **tekin** |
| Fon musiqa | `assets/music/` ga bir nechta mp3 tashlang (royalty-free) | tekin |

> ⚠️ **Rasm generatorlar video emas, rasm chiqaradi.** Shuning uchun video =
> 6 ta AI rasm + Ken Burns zoom + o'tish effektlari + ovoz + subtitr.
> Bu Shorts'da eng ko'p ishlatiladigan format va deyarli tekin.
> Haqiqiy harakatlanuvchi video kerak bo'lsa — Veo API (~$0.4/sek, ancha qimmat).

---

## 2. O'rnatish

```bash
cd shorts_factory
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

copy .env.example .env        # Windows  (Linux: cp .env.example .env)
```

`.env` ni oching va kalitlarni yozing:

```ini
GEMINI_API_KEY=AIza...
TELEGRAM_BOT_TOKEN=123456:AA...
TELEGRAM_CHAT_ID=@mening_kanalim
YOUTUBE_ENABLED=true
```

YouTube uchun bir marta:

```bash
python youtube_auth.py     # brauzer ochiladi → hisobni tanlang → youtube_token.json yaratiladi
```

---

## 3. Ishlatish

```bash
python run.py                  # 1 ta video: yasaydi + Telegram + YouTube
python run.py --count 3        # ketma-ket 3 ta
python run.py --no-publish     # faqat yasaydi, hech qayerga yubormaydi
python run.py --idea-only      # faqat skriptni ko'rsatadi (tekin, tez tekshirish)
python run.py --scenes 8       # uzunroq video
```

Natija: `output/2026-09-07_.../` ichida `*.mp4`, `thumb.jpg`, `idea.json`, rasmlar.

Ovozni almashtirish:

```bash
python core/tts.py en          # mavjud inglizcha ovozlar ro'yxati
```
keyin `.env` da `VOICE=en-US-BrianMultilingualNeural` kabi yozing.

---

## 4. ⭐ Onlayn ishlatish (GitHub Actions — kompyuter o'chiq bo'lsa ham)

Butun konveyer GitHub serverlarida ishlaydi. Sizdan hech narsa talab qilinmaydi —
faqat Telegramga kelgan videoni ko'rib **✅ tugmasini bosasiz**.

```
09:00  GitHub o'zi video yasaydi  →  Telegramga [✅ Yukla] [🗑 Bekor] bilan keladi
18:00  yana bittasi
       ✅ ni bosdingiz  →  10 daqiqa ichida YouTube kanalga chiqadi
```

### Chiqarish (bir buyruq)

**1)** GitHub token oling — https://github.com/settings/tokens/new
   → Note: `shorts-factory`, Expiration: `No expiration`
   → belgilang: ☑ **repo**  ☑ **workflow** → *Generate token* → nusxa oling

**2)** `.env` ga yozing:
```ini
GITHUB_TOKEN=ghp_...
```

**3)** ishga tushiring:
```bash
python deploy.py
```

Bu skript o'zi hamma narsani qiladi: repo yaratadi → kodni push qiladi →
kalitlarni shifrlab Secrets'ga yozadi → jadvalni yoqadi → sinov videosini boshlaydi.
`gh` CLI o'rnatish shart emas, faqat `git` bo'lsa bo'ldi.

> **Repo `public` bo'ladi** — chunki ochiq repolarda GitHub Actions daqiqalari
> **cheksiz va tekin**. Kalitlaringiz kodda emas, Secrets ichida — hech kim ko'rmaydi.
> Yopiq repo xohlasangiz `deploy.py` da `"private": False` → `True` qiling va
> `workflows/approve.yml` da cron'ni `*/30 * * * *` ga o'zgartiring
> (oyiga 2000 daqiqa limitiga sig'ish uchun).

### Qo'lda boshqarish

```bash
gh workflow run generate.yml               # hozir yangi video yasa
gh workflow run generate.yml -f count=3    # 3 ta
gh workflow run approve.yml                # tugma bosishlarini darhol tekshir
gh run list --limit 5                      # oxirgi ishlar
```

Yoki GitHub sahifasida: **Actions → Shorts yasash → Run workflow**.

### Qanday ishlaydi

| Fayl | Vazifa |
|---|---|
| `.github/workflows/generate.yml` | 04:00 va 13:00 UTC (= 09:00 / 18:00 Toshkent) da video yasaydi, Telegramga tugmalar bilan yuboradi, mp4 ni artifact sifatida 30 kun saqlaydi |
| `.github/workflows/approve.yml` | har 10 daqiqada Telegram tugmalarini tekshiradi; ✅ bosilgan bo'lsa artifact'ni olib YouTube'ga yuklaydi va xabar tagidagi matnni link bilan yangilaydi |
| `state/pending/*.json` | tasdiq kutayotgan videolar |
| `state/history.json` | ilgari chiqqan mavzular — Agent 1 takrorlamaydi |

Tasdiqsiz, darhol yuklansin desangiz: repo → Settings → Variables emas,
`generate.yml` dagi `APPROVAL_MODE: "true"` ni `"false"` qiling.

---

## 4b. Lokal avtomatlashtirish (muqobil)

**Windows — Task Scheduler:** `run.bat` ni kuniga 1–3 marta ishga tushirishga qo'ying.

**Linux/Mac — cron:**
```cron
0 9,18 * * * cd /path/shorts_factory && .venv/bin/python run.py >> log.txt 2>&1
```

---

## 5. Nimani sozlash mumkin

`.env` ichida:

- `NICHE` — mavzu yo'nalishi (`mind-blowing history and science facts`)
- `SCENES` — sahnalar soni (6 ≈ 40 sek)
- `IMAGE_STYLE` — vizual uslub (`cinematic photoreal…` yoki `dark comic book…`)
- `VOICE`, `MUSIC_VOLUME`, `YOUTUBE_PRIVACY`

Subtitr ko'rinishi: `core/subtitles.py` (shrift, rang, o'lcham, joylashuv).
Video effektlari: `core/video.py` (`_kenburns`, `XFADE`).
Skript qoidalari: `agents/idea_agent.py` → `PROMPT`.

---

## 6. Tez-tez uchraydigan muammolar

| Xato | Yechim |
|---|---|
| `ffmpeg xato` / `not found` | ffmpeg PATH da emas |
| `javobda rasm yo'q` | promt moderatsiyadan o'tmadi — kod avtomat qayta uradi, keyin fallback modelga o'tadi |
| Telegram `413`/timeout | video 50 MB dan katta — `SCENES` ni kamaytiring yoki `crf` ni 23 qiling |
| YouTube `quotaExceeded` | kunlik limit ~6 ta yuklash. Ertaga davom etadi |
| YouTube thumbnail qo'yilmadi | kanal telefon orqali tasdiqlanmagan |
| `youtube_token.json yo'q` | `python youtube_auth.py` |

---

## 7. Fayl tuzilishi

```
shorts_factory/
├── run.py                 # orkestrator (1 video yasab, publish qiladi)
├── approve.py             # Telegram tugmalarini o'qib YouTube'ga yuklaydi
├── deploy.py              # bir buyruq bilan GitHub'ga chiqarish
├── youtube_auth.py        # 1 martalik OAuth (+ CI uchun refresh token chiqaradi)
├── config.py / .env
├── .github/workflows/
│   ├── generate.yml       # jadval: 09:00 va 18:00 (Toshkent)
│   └── approve.yml        # har 10 daq: tasdiqlarni tekshiradi
├── agents/
│   ├── idea_agent.py      # AGENT 1
│   ├── render_agent.py    # AGENT 2
│   └── publish_agent.py   # AGENT 3
├── core/
│   ├── llm.py             # Gemini text (JSON schema)
│   ├── images.py          # Nano Banana 9:16
│   ├── tts.py             # edge-tts + so'z vaqtlari
│   ├── subtitles.py       # ASS pop-up subtitr
│   ├── video.py           # ffmpeg Ken Burns + xfade + mix
│   ├── telegram.py        # sendVideo, inline tugmalar, getUpdates
│   └── state.py           # takrorlanmaslik tarixi
├── assets/music/          # fon musiqa (mp3)
├── state/
│   ├── history.json       # chiqqan mavzular
│   └── pending/*.json     # tasdiq kutayotganlar
└── output/
```
