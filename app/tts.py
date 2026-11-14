"""Озвучка башкирского текста моделью MMS-TTS (facebook/mms-tts-bak).
Модуль необязательный: если torch/transformers не установлены (install_tts.bat), сервер отвечает 503,
а сайт озвучивает фрагмент голосом браузера. Готовые файлы кэшируются в data/tts/."""
import hashlib, io, os, threading, wave
from pathlib import Path

MODEL = os.getenv("TTS_MODEL", "facebook/mms-tts-bak")
CACHE = Path(os.getenv("TTS_CACHE", Path(__file__).parent / "data" / "tts"))
# Готовая озвучка, которая лежит в репозитории: на сервере без модели (бесплатный хостинг)
# фрагменты звучат из этой папки. Собирается на своём компьютере: voice_pack.bat
PACK = Path(__file__).parent / "voice"
_lock = threading.Lock()
_m = {}

def available():
    if os.getenv("TTS_DISABLED") == "1": return False
    try:
        import torch, transformers  # noqa: F401
        return True
    except Exception:
        return False

def _load():
    if "model" not in _m:
        from transformers import VitsModel, AutoTokenizer
        _m["tok"] = AutoTokenizer.from_pretrained(MODEL)
        _m["model"] = VitsModel.from_pretrained(MODEL).eval()
    return _m["tok"], _m["model"]

def _name(text):
    text = " ".join(text.split())[:400]
    return text, hashlib.sha1(f"{MODEL}|{text}".encode()).hexdigest() + ".wav"

def ready(text):
    """Готовый файл озвучки, если он уже есть (в кэше или в папке voice), иначе None."""
    _, name = _name(text)
    for d in (CACHE, PACK):
        if (d / name).exists(): return d / name
    return None

def has_pack():
    return PACK.exists() and any(PACK.glob("*.wav"))

def synth(text):
    try:
        return _synth(text)
    except Exception as e:   # модель не скачалась, нет памяти и т. п. — сайт перейдёт на голос браузера
        print(f"[Тамға] озвучка не удалась: {e!r}")
        return None

def _synth(text):
    text, name = _name(text)
    out = CACHE / name
    got = ready(text)
    if got: return got
    if not available(): return None
    import torch
    with _lock:
        tok, model = _load()
        src = text
        if getattr(tok, "is_uroman", False):
            try:
                import uroman as ur
                src = ur.Uroman().romanize_string(text)
            except Exception:
                return None
        inp = tok(src, return_tensors="pt")
        with torch.no_grad():
            wav = model(**inp).waveform[0].numpy()
    pcm = (wav.clip(-1, 1) * 32767).astype("int16").tobytes()
    CACHE.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(model.config.sampling_rate); w.writeframes(pcm)
    out.write_bytes(buf.getvalue())
    return out
