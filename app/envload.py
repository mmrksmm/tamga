"""Загрузка локального .env и безопасные значения конфигурации по умолчанию."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Несекретные настройки: они входят в проект и не требуют ручного ввода.
DEFAULTS = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "465",
    "SMTP_USER": "lingtamga.edu@gmail.com",
    "SMTP_FROM": "lingtamga.edu@gmail.com",
    "CONSENSUS_MIN_VOTERS": "3",
    "CONSENSUS_NOISE": "0.2",
    "CONSENSUS_SHARE": "0.6",
    "CONSENSUS_WORD_SIM": "0.7",
    "XP_CONFIRMED": "10",
    "XP_CATCH": "5",
    "XP_FLAME": "15",
    "STREAK_REPAIR_XP": "100",
    "PLANT_RATE": "0.3",
    "REG_PER_IP": "80",
    "DEV_SHOW_CODE": "1",
    "BOT_USERNAME": "tamga_school_bot",
    "BOT_TZ": "Asia/Yekaterinburg",
    "REMIND_FROM": "8",
    "DEMO_SEED": "1",
    "DATABASE_URL": "sqlite:///./tamga_v5.db",
    "AUTO_IMPORT": "kk,alt,ar,sah,zh",
    "AUTO_IMPORT_SCHOOLS": "1",
    "TRUST_PROXY": "0",
    "ASR_MODEL": "small",
    "ASR_LANG": "ba",
    "ASR_MAX_MINUTES": "30",
    "TTS_MODEL": "facebook/mms-tts-bak",
}

# Сначала читаем локальный .env: секреты и пользовательские переопределения.
for path in (ROOT / ".env", Path(__file__).parent / ".env"):
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# Значения по умолчанию применяются только если пользователь их не переопределил.
for key, value in DEFAULTS.items():
    os.environ.setdefault(key, value)
