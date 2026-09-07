"""GitHub'ga bir buyruq bilan chiqarish — `gh` CLI kerak emas, faqat token.

TOKEN OLISH (1 daqiqa):
  https://github.com/settings/tokens/new
    Note: shorts-factory
    Expiration: No expiration
    Scopes:  ☑ repo    ☑ workflow
  -> Generate token -> nusxa oling (ghp_... )
  -> .env fayliga yozing:  GITHUB_TOKEN=ghp_...

ISHGA TUSHIRISH:
  python deploy.py                 # repo nomi: shorts-factory
  python deploy.py my-repo-nomi

Nima qiladi:
  1. GitHub'da repo yaratadi (public — Actions daqiqalari cheksiz tekin)
  2. kodni push qiladi
  3. hamma kalitni Secrets/Variables'ga shifrlab yozadi
  4. birinchi sinov videosini ishga tushiradi
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402

ROOT = config.ROOT
API = "https://api.github.com"


# ---------------- yordamchilar ----------------
def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "shorts-factory",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        raise RuntimeError(f"GitHub API {method} {path} -> {e.code}: {detail}") from None


def sh(cmd: list[str], check: bool = True, quiet: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if not quiet and p.stdout.strip():
        print("   ", p.stdout.strip()[:300])
    if check and p.returncode != 0:
        raise SystemExit(f"❌ {' '.join(cmd)}\n{(p.stderr or p.stdout)[-800:]}")
    return p


def encrypt(pub_key_b64: str, value: str) -> str:
    from nacl import encoding, public
    pk = public.PublicKey(pub_key_b64.encode(), encoding.Base64Encoder())
    return base64.b64encode(public.SealedBox(pk).encrypt(value.encode())).decode()


def install_workflows() -> None:
    """workflows/*.yml -> .github/workflows/"""
    src, dst = ROOT / "workflows", ROOT / ".github" / "workflows"
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for y in src.glob("*.yml"):
        shutil.copy2(y, dst / y.name)


def yt_creds() -> dict:
    out = {}
    if config.YOUTUBE_TOKEN_FILE.exists():
        t = json.loads(config.YOUTUBE_TOKEN_FILE.read_text())
        out = {
            "YOUTUBE_REFRESH_TOKEN": t.get("refresh_token", ""),
            "YOUTUBE_CLIENT_ID": t.get("client_id", ""),
            "YOUTUBE_CLIENT_SECRET_VALUE": t.get("client_secret", ""),
        }
    for k in list(out):
        out[k] = out[k] or os.getenv(k, "")
    return {k: v for k, v in out.items() if v}


ASK = {
    "GEMINI_API_KEY": (
        "GEMINI API KALITI  (skript va zaxira rasm generatori uchun)",
        "  Qayerdan: https://aistudio.google.com/apikey  ->  Create API key",
        "  Ko'rinishi: AQ.Ab8... (yangi) yoki AIza... (eski)",
        lambda v: (v.startswith("AQ.") or v.startswith("AIza")) and len(v) > 25,
        "kalit 'AQ.' yoki 'AIza' bilan boshlanishi kerak",
    ),
    "TELEGRAM_BOT_TOKEN": (
        "TELEGRAM BOT TOKENI",
        "  Qayerdan: Telegramda @BotFather -> /newbot",
        "  Ko'rinishi: 123456789:AAH...",
        lambda v: ":" in v and v.split(":")[0].isdigit(),
        "token 'raqamlar:harflar' ko'rinishida bo'lishi kerak",
    ),
    "TELEGRAM_CHAT_ID": (
        "TELEGRAM KANAL / CHAT",
        "  Kanal yarating -> botni ADMIN qiling -> kanal manzilini yozing.",
        "  Ko'rinishi: @mening_kanalim   (yoki raqamli id: -1001234567890)",
        lambda v: v.startswith("@") or v.lstrip("-").isdigit(),
        "@ bilan boshlanishi yoki raqamli id bo'lishi kerak",
    ),
}


def ask_missing(secrets: dict) -> dict:
    """Yetishmayotgan kalitlarni so'raydi va .env ga saqlaydi."""
    need = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
            if not secrets.get(k)]
    if not need:
        return secrets

    print("\n" + "=" * 64)
    print(f"  {len(need)} ta kalit yetishmayapti. Har birini joylab Enter bosing.")
    print("  (o'tkazib yuborish uchun bo'sh qoldirib Enter)")
    print("=" * 64)

    for k in need:
        title, where, shape, ok, hint = ASK[k]
        while True:
            print(f"\n--- {title}")
            print(where)
            print(shape)
            v = input(f"{k} = ").strip()
            if not v:
                print("    o'tkazib yuborildi")
                break
            if ok(v):
                secrets[k] = v
                break
            print(f"    ! {hint} — qayta urinib ko'ring")

    save_env({k: v for k, v in secrets.items() if v})
    return secrets


def save_env(values: dict) -> None:
    """.env dagi qatorlarni yangilaydi (qolganini tegmaydi)."""
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    for key, val in values.items():
        found = False
        for i, ln in enumerate(lines):
            if ln.split("=", 1)[0].strip() == key:
                lines[i] = f"{key}={val}"
                found = True
                break
        if not found:
            lines.append(f"{key}={val}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n   ✓ .env yangilandi")


# Eskirgan qiymatlarni yangilash (model nomlari o'zgargan)
MIGRATE = {
    "TEXT_MODEL": {"gemini-3-flash": "gemini-3.5-flash",
                   "gemini-3-flash-preview": "gemini-3.5-flash"},
    "POLLI_MODEL": {"flux": "sana"},          # flux tekin rejadan olib tashlangan
    "IMAGE_MODEL": {"gemini-3.1-flash-image-preview": "gemini-3.1-flash-image"},
}


def read_env() -> dict:
    env = ROOT / ".env"
    out = {}
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def migrate_env() -> dict:
    """.env dagi eskirgan qiymatlarni almashtiradi va yangi holatni qaytaradi."""
    cur = read_env()
    fixed = {}
    for key, table in MIGRATE.items():
        v = cur.get(key, "")
        if v in table:
            fixed[key] = table[v]
            print(f"    ↻ {key}: {v} -> {table[v]}")
    if fixed:
        save_env(fixed)
        cur.update(fixed)
    return cur


# ---------------- asosiy ----------------
def main() -> None:
    repo_name = sys.argv[1] if len(sys.argv) > 1 else "shorts-factory"

    # token: argv[2] -> muhit o'zgaruvchisi -> .env -> so'rash
    token = (sys.argv[2] if len(sys.argv) > 2 else "").strip()
    if not token or token.endswith("..."):
        token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token or token.endswith("..."):
        print("\n" + "=" * 60)
        print("  GitHub tokenini shu yerga joylang va Enter bosing.")
        print("  (sichqonchaning O'NG tugmasi = joylash, yoki Ctrl+V)")
        print("=" * 60)
        token = input("\nToken: ").strip()
    if not token:
        raise SystemExit("❌ Token kerak")
    print(f"   token: {len(token)} belgi, {token[:8]}…{token[-4:]}")
    save_env({"GITHUB_TOKEN": token})

    try:
        import nacl  # noqa: F401
    except ImportError:
        print("▶ pynacl o'rnatilmoqda…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pynacl"], check=True)

    me = api("GET", "/user", token)
    owner = me["login"]
    full = f"{owner}/{repo_name}"
    print(f"\n👤 {owner}")

    secrets = {
        "GEMINI_API_KEY": config.GEMINI_API_KEY,
        "TELEGRAM_BOT_TOKEN": config.TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": config.TELEGRAM_CHAT_ID,
        **yt_creds(),
    }
    secrets = ask_missing(secrets)

    # 1. repo
    print("\n▶ Repo…")
    try:
        api("GET", f"/repos/{full}", token)
        print(f"    '{full}' allaqachon bor")
    except RuntimeError:
        api("POST", "/user/repos", token, {
            "name": repo_name,
            "description": "Avtomat YouTube Shorts konveyeri (Gemini + Nano Banana + Telegram)",
            "private": False,          # public -> Actions cheksiz tekin
            "has_issues": False, "has_wiki": False, "has_projects": False,
        })
        print(f"    ✓ yaratildi: https://github.com/{full}")

    # 2. push
    print("\n▶ Kod yuklanmoqda…")
    install_workflows()
    if not (ROOT / ".git").exists():
        sh(["git", "init", "-b", "main"])
    sh(["git", "config", "user.name", owner])
    sh(["git", "config", "user.email", f"{owner}@users.noreply.github.com"])
    sh(["git", "add", "-A"])
    sh(["git", "commit", "-m", "Shorts Factory"], check=False)
    sh(["git", "remote", "remove", "origin"], check=False)
    sh(["git", "remote", "add", "origin",
        f"https://x-access-token:{token}@github.com/{full}.git"])
    sh(["git", "branch", "-M", "main"])
    sh(["git", "push", "-u", "origin", "main", "--force"], quiet=False)
    # tokenni remote URL'da qoldirmaymiz
    sh(["git", "remote", "set-url", "origin", f"https://github.com/{full}.git"])
    print("    ✓ push tayyor")

    # 3. secrets
    print("\n▶ Secrets…")
    pk = api("GET", f"/repos/{full}/actions/secrets/public-key", token)
    for k, v in secrets.items():
        if not v:
            continue
        api("PUT", f"/repos/{full}/actions/secrets/{k}", token,
            {"encrypted_value": encrypt(pk["key"], v), "key_id": pk["key_id"]})
        print(f"    ✓ {k}")

    # 4. variables
    print("\n▶ Variables…")
    env = migrate_env()

    def val(key, fallback):
        return env.get(key) or fallback

    for k, v in [("NICHE", val("NICHE", config.NICHE)),
                 ("VOICE", val("VOICE", config.VOICE)),
                 ("SCENES", val("SCENES", str(config.SCENES))),
                 ("YOUTUBE_PRIVACY", val("YOUTUBE_PRIVACY", config.YOUTUBE_PRIVACY)),
                 ("IMAGE_PROVIDER", val("IMAGE_PROVIDER", config.IMAGE_PROVIDER)),
                 ("POLLI_MODEL", val("POLLI_MODEL", "sana")),
                 ("TEXT_MODEL", val("TEXT_MODEL", "gemini-3.5-flash")),
                 ("HANDOFF_WAIT", val("HANDOFF_WAIT", str(config.HANDOFF_WAIT)))]:
        try:
            api("POST", f"/repos/{full}/actions/variables", token, {"name": k, "value": v})
        except RuntimeError:
            api("PATCH", f"/repos/{full}/actions/variables/{k}", token, {"name": k, "value": v})
        print(f"    ✓ {k} = {v}")

    # 5. sinov
    print("\n▶ Sinov videosi ishga tushirilmoqda…")
    try:
        api("POST", f"/repos/{full}/actions/workflows/generate.yml/dispatches", token,
            {"ref": "main", "inputs": {"count": "1"}})
        print("    ✓ boshlandi")
    except RuntimeError as e:
        print(f"    ! qo'lda ishga tushiring (Actions -> Run workflow): {e}")

    print(f"""
✅ Tayyor!

   Repo:     https://github.com/{full}
   Actions:  https://github.com/{full}/actions

   Har kuni 09:00 va 18:00 (Toshkent) da o'zi video yasaydi va Telegramga
   [✅ Yukla] [🗑 Bekor] tugmalari bilan yuboradi.
   ✅ bosganingizdan keyin 10 daqiqa ichida YouTube kanalga chiqadi.
""")


if __name__ == "__main__":
    main()
