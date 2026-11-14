"""Пошаговая установка и запуск сайта и Telegram-бота."""
import getpass, json, os, re, subprocess, sys, threading, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
ENV = ROOT / ".env"
PY = sys.executable
STEPS = 6

def env_get(key):
    value = os.environ.get(key)
    if value is not None:
        return value
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].split("#")[0].strip().strip('"').strip("'")
    return ""

def save_env(values):
    """Сохраняет локальные секреты в .env, не перезаписывая другие настройки."""
    current = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                current[k.strip()] = v.strip()
    current.update({k: v for k, v in values.items() if v})
    ENV.write_text(
        "".join(f"{k}={v}\n" for k, v in current.items()),
        encoding="utf-8"
    )

def configure_secrets():
    """Спрашивает только секреты; обычные настройки уже заданы в app/envload.py."""
    sys.path.insert(0, str(APP))
    import envload  # noqa: F401

    secret_fields = [
        ("TELEGRAM_TOKEN", "Токен Telegram-бота от @BotFather"),
        ("API_KEY", "API_KEY для внешнего доступа (Enter — пропустить)"),
        ("SMTP_PASSWORD", "Пароль приложения почты (Enter — без отправки писем)"),
    ]
    print("\nПервоначальная настройка секретов")
    print("При вводе секретных данных символы НЕ отображаются — это нормально.")
    print("Если значение уже сохранено, повторно вводить его не нужно.\n")
    changed = {}
    for key, label in secret_fields:
        if env_get(key):
            continue
        try:
            value = getpass.getpass(label + " [ввод скрыт]: ").strip()
        except (EOFError, KeyboardInterrupt):
            value = ""
        if value:
            changed[key] = value
            os.environ[key] = value
    if changed:
        save_env(changed)
        print("\nНастройки сохранены.\n")
    else:
        print("\nНовые секреты не добавлены. Необязательные функции будут отключены.\n")


def banner(step, title):
    done = round(100 * (step - 1) / STEPS)
    print(f"\n{'─' * 62}\n  ШАГ {step}/{STEPS} ({done}% пути пройдено) · {title}\n{'─' * 62}")

def say(msg): print("  " + msg)

def fail(msg):
    print("\n  ОШИБКА: " + msg)
    input("  Нажмите Enter, чтобы закрыть... ")
    sys.exit(1)

def pip_install(req, what, critical):
    """pip сам показывает полосу загрузки каждого пакета (сколько МБ скачано)."""
    say(f"Устанавливаю {what} — ниже pip показывает загрузку каждого пакета...")
    r = subprocess.run([PY, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / req)])
    if r.returncode != 0:
        if critical: fail(f"не удалось установить пакеты из {req}. Проверьте интернет и запустите demo.bat ещё раз.")
        say(f"Не получилось установить {what} — пропускаю (сайт будет использовать голос браузера).")
        return False
    return True

def have(*mods):
    return subprocess.run([PY, "-c", "import " + ",".join(mods)], capture_output=True).returncode == 0

def download(url, dest, what):
    """Скачивание файла с процентами."""
    state = {"p": -1}
    def hook(blocks, bs, total):
        if total > 0:
            p = min(100, blocks * bs * 100 // total)
            if p != state["p"]:
                state["p"] = p
                print(f"\r  Скачиваю {what}: {p}% ({min(blocks * bs, total) // 1048576} / {total // 1048576} МБ)", end="", flush=True)
    urllib.request.urlretrieve(url, dest, hook)
    print()

# ---------- конфигурация и секреты ----------
configure_secrets()
if ":" not in (env_get("TELEGRAM_TOKEN") or ""):
    os.environ["TELEGRAM_TOKEN"] = ""  # без токена сайт работает, бот не запускается
    say("\n  ВНИМАНИЕ: TELEGRAM_TOKEN не задан — Telegram-бот не запустится.")
    say("  Сайт при этом будет работать полностью.\n")

# ---------- шаг 1: базовые пакеты ----------
banner(1, "Базовые пакеты сайта и бота")
if have("fastapi", "uvicorn", "aiogram", "sqlalchemy", "argon2"):
    say("Уже установлены — пропускаю.")
else:
    pip_install("requirements.txt", "базовые пакеты (~50 МБ)", critical=True)

# ---------- шаг 2: пакеты озвучки ----------
banner(2, "Башкирская озвучка (TTS): библиотеки")
tts_ok = have("torch", "transformers")
if tts_ok:
    say("Уже установлены — пропускаю.")
else:
    say("Это самый долгий шаг первого запуска: около 1 ГБ.")
    tts_ok = pip_install("requirements-tts.txt", "библиотеки озвучки", critical=False)

# ---------- шаг 3: модель озвучки ----------
banner(3, "Башкирская озвучка (TTS): модель facebook/mms-tts-bak")
if tts_ok:
    code = ("from huggingface_hub import snapshot_download\n"
            "snapshot_download('facebook/mms-tts-bak')\n")
    say("Проверяю и скачиваю модель (~150 МБ): huggingface показывает проценты сам...")
    if subprocess.run([PY, "-c", code]).returncode == 0:
        say("Модель на месте.")
    else:
        say("Модель скачать не удалось — фрагменты будет читать голос браузера.")
else:
    say("Библиотеки озвучки не установлены — шаг пропущен.")

# ---------- что уже загружено в базу ----------
langs = [l.strip() for l in (env_get("AUTO_IMPORT") or "kk,alt,ar,sah,zh").split(",") if l.strip()]
check = (
    "import json,sys\n"
    "sys.path.insert(0,'.')\n"
    "import envload\n"
    "from models import SessionLocal, Fragment, School, Base, engine, ensure_columns\n"
    "Base.metadata.create_all(engine); ensure_columns()\n"
    "langs=[l for l in sys.argv[1].split(',') if l]\n"
    "s=SessionLocal()\n"
    "missing=[l for l in langs if not s.query(Fragment.id).filter(Fragment.chapter==f'разговорник ba-ru-{l}').first()]\n"
    "print(json.dumps({'missing':missing,'schools':s.query(School).count()<100}))\n"
)
r = subprocess.run([PY, "-c", check, ",".join(langs)], cwd=APP, capture_output=True, text=True)
state = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {"missing": langs, "schools": True}

# ---------- шаг 4: датасеты ----------
banner(4, "Датасеты разговорников (фразы для заданий)")
missing = state["missing"]
if not missing:
    say("Все датасеты уже в базе — пропускаю.")
for i, l in enumerate(missing, 1):
    say(f"Датасет {i}/{len(missing)}: пара ba-{l} (проценты — ниже)")
    if subprocess.run([PY, str(ROOT / "import_hf.py"), "--lang", l], cwd=APP).returncode != 0:
        say(f"Пара ba-{l} не загрузилась (нет интернета?) — продолжаю без неё.")

# ---------- шаг 5: школы ----------
banner(5, "Список школ Башкортостана (для рейтингов и кодов классов)")
if not state["schools"]:
    say("Список школ уже в базе — пропускаю.")
else:
    say("Загружаю школы с shkola.city — на каждом районе видно, сколько процентов готово (10–20 минут)...")
    if subprocess.run([PY, str(ROOT / "import_schools.py")], cwd=APP).returncode != 0:
        say("Полный список школ не загрузился — останется короткий встроенный список, это не мешает работе.")

# ---------- шаг 6: публичная ссылка и запуск ----------
banner(6, "Публичная ссылка Cloudflare и запуск")
url = "http://127.0.0.1:8000"
exe = ROOT / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
if os.name == "nt" and not exe.exists():
    try:
        download("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
                 exe, "cloudflared (~60 МБ, один раз)")
    except Exception as e:
        say(f"Не удалось скачать cloudflared: {e}")
        say("Сайт будет доступен только на этом компьютере и в той же Wi-Fi.")
tunnel = None
if exe.exists():
    tunnel = subprocess.Popen([str(exe), "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    found = []
    def read():
        for line in tunnel.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m and not found: found.append(m.group(0))
    threading.Thread(target=read, daemon=True).start()
    say("Получаю публичную ссылку...")
    for _ in range(60):
        if found: break
        time.sleep(1)
    if found:
        url = found[0]
        # новая ссылка появляется в интернете не сразу; если открыть раньше, Windows запомнит «адрес не найден»
        say("Ссылка получена, жду, пока она заработает (до минуты)...")
        for _ in range(30):
            try:
                req = urllib.request.Request("https://1.1.1.1/dns-query?name=" + url.split("//")[1] + "&type=A",
                                             headers={"accept": "application/dns-json"})
                if '"Answer"' in urllib.request.urlopen(req, timeout=5).read().decode(): break
            except Exception: pass
            time.sleep(2)
        time.sleep(5)
    else: say("Публичная ссылка не появилась — сайт будет доступен только локально.")

# всё уже загружено выше, поэтому фоновые импорты при старте сайта отключаем:
# сайт не должен ничего докачивать после запуска
os.environ["AUTO_IMPORT"] = ""
os.environ["AUTO_IMPORT_SCHOOLS"] = "0"
os.environ["RUN_BOT"] = "1"           # бот работает внутри сайта, одно окно на всё
os.environ["PUBLIC_URL"] = url        # ссылки «Войти на сайт» из бота ведут сюда

print("\n" + "=" * 62)
print("  ГОТОВО: 100%. Всё загружено, запускаю сайт.")
print("  САЙТ:", url)
print("  Открывайте эту ссылку с любого телефона или компьютера.")
if ":" in (os.environ.get("TELEGRAM_TOKEN") or env_get("TELEGRAM_TOKEN") or ""):
    print("  БОТ: напишите своему боту в Telegram /start")
if env_get("DEMO_SEED") == "1":
    print("  ВХОД (демо-аккаунты, пароль у всех demo123):")
    print("    админ admin@demo.ru · учитель teacher@demo.ru · ученик student@demo.ru · эксперт expert@demo.ru")
print("  Пока это окно открыто — всё работает. Остановить: Ctrl+C")
print("  Ссылка меняется при каждом запуске.")
print("=" * 62 + "\n")
if url.startswith("https") and os.name == "nt":
    os.system(f"start {url}")
try:
    subprocess.run([PY, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000",
                    "--proxy-headers", "--forwarded-allow-ips=*"], cwd=APP)
finally:
    if tunnel: tunnel.terminate()
