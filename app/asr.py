"""Автоматическая разметка аудио: расшифровка речи и разметка по паузам.

Модуль необязательный. Нужен пакет faster-whisper (install_asr.bat); без него сайт
отвечает 503, а учитель расставляет отметки времени вручную.

Два режима:
  • «расшифровать» — модель сама находит границы предложений и пишет текст;
  • «по паузам»    — текст у учителя уже есть, программа только раскладывает
                     предложения по звучащим кускам записи (точнее и быстрее).
"""
import os, re, threading

MODEL = os.getenv("ASR_MODEL", "small")        # можно указать свою модель, см. README
LANG = os.getenv("ASR_LANG", "ba")
MAX_MINUTES = int(os.getenv("ASR_MAX_MINUTES", "30"))
_lock = threading.Lock()
_m = {}


def is_hf(model=None):
    """Имя с косой чертой — это модель с Hugging Face (например, башкирская
    AigizK/bashkir-whisper-small). Такие запускаются через transformers, а короткие
    имена вроде small — через faster-whisper."""
    return "/" in (model or MODEL)


def can_pauses():
    """Разметка по паузам требует только чтения звука — ни модели, ни интернета."""
    if os.getenv("ASR_DISABLED") == "1": return False
    try:
        import av  # noqa: F401
        return True
    except Exception:
        return False


def available():
    """Расшифровка речи: нужен и декодер звука, и сама модель."""
    if not can_pauses(): return False
    try:
        if is_hf():
            import transformers, torch  # noqa: F401
        else:
            import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


# ---------- чтение звука (любой формат: mp3, m4a, ogg, wav, flac, webm) ----------
def read_pcm(path, sr=16000):
    import av, numpy as np
    parts = []
    with av.open(str(path)) as c:
        st = next((s for s in c.streams if s.type == "audio"), None)
        if st is None: raise RuntimeError("В файле нет звуковой дорожки")
        rs = av.AudioResampler(format="s16", layout="mono", rate=sr)
        for frame in c.decode(st):
            for f in rs.resample(frame): parts.append(f.to_ndarray().reshape(-1))
        for f in rs.resample(None) or []: parts.append(f.to_ndarray().reshape(-1))
    if not parts: raise RuntimeError("Не удалось прочитать звук")
    x = np.concatenate(parts).astype("float32") / 32768.0
    return x, sr


def speech_spans(x, sr, win=0.03, min_sil=0.45, min_len=0.35, pad=0.15):
    """Куски, где звучит речь: тихие места длиннее min_sil считаются паузами."""
    import numpy as np
    e, win = energy(x, sr, win)
    p95, p10 = float(np.percentile(e, 95)), float(np.percentile(e, 10))
    thr = max(p95 * 0.06, p10 * 1.8, 1e-4)          # громкость речи и уровень фонового шума
    if float((e > thr).mean()) < 0.02:              # запись звучит ровно, без тихих мест
        thr = max(p95 * 0.06, 1e-4)
    loud = e > thr
    spans, start, gap = [], None, 0
    for i, v in enumerate(loud):
        if v:
            if start is None: start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap * win >= min_sil:
                spans.append((start * win, (i - gap) * win)); start = None; gap = 0
    if start is not None: spans.append((start * win, len(loud) * win))
    out = []
    for a, b in spans:
        if b - a >= min_len: out.append((max(0.0, a - pad), b + pad))
    return out


SENT = re.compile(r"[^.!?…\n]+[.!?…]*")

def sentences(text):
    return [s.strip() for s in SENT.findall(text) if len(s.strip()) >= 3]


def energy(x, sr, win=0.03):
    import numpy as np
    n = max(1, int(win * sr))
    return np.sqrt(np.add.reduceat(x.astype("float64") ** 2, np.arange(0, len(x), n)) / n), win


def fit_spans(spans, k, e, win):
    """Подогнать число звучащих кусков под число предложений в тексте."""
    import numpy as np
    spans = [list(s) for s in spans]
    while len(spans) > k:                                   # лишние куски склеиваем по самой короткой паузе
        i = min(range(len(spans) - 1), key=lambda i: spans[i + 1][0] - spans[i][1])
        spans[i:i + 2] = [[spans[i][0], spans[i + 1][1]]]
    while len(spans) < k:                                   # кусков мало — режем самый длинный в самом тихом месте
        i = max(range(len(spans)), key=lambda i: spans[i][1] - spans[i][0])
        a, b = spans[i]
        lo, hi = int(a / win) + 3, int(b / win) - 3
        if hi - lo < 2: mid = (a + b) / 2
        else: mid = (lo + int(np.argmin(e[lo:hi]))) * win
        spans[i:i + 1] = [[a, mid], [mid, b]]
    return [tuple(s) for s in spans]


def by_pauses(path, text):
    """Готовый текст раскладывается по звучащим кускам записи."""
    x, sr = read_pcm(path)
    return by_pauses_x(x, sr, text)


def by_pauses_x(x, sr, text):
    dur = len(x) / sr
    sents = sentences(text)
    if not sents: raise RuntimeError("В тексте не нашлось законченных предложений — проверьте точки в конце")
    spans = speech_spans(x, sr)
    if not spans: raise RuntimeError("В записи не нашлось речи — возможно, файл слишком тихий")
    e, win = energy(x, sr)
    spans = fit_spans(spans, len(sents), e, win)
    # Границы фрагментов идут встык: каждый звучит до начала следующего, чтобы ничего не обрезалось.
    rows = []
    for i, ((a, _b), s) in enumerate(zip(spans, sents)):
        end = spans[i + 1][0] if i + 1 < len(spans) else dur
        rows.append((int(a), max(int(a) + 1, int(end)), s))
    return rows


# ---------- расшифровка речи ----------
def _load():
    if "m" not in _m:
        if is_hf():
            from transformers import pipeline, GenerationConfig, AutoModelForSpeechSeq2Seq, AutoProcessor
            model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL)
            # Дообученные модели часто сохранены старой версией библиотеки: в их настройках нет
            # полей для отметок времени. Берём эти настройки у исходной модели, язык оставляем свой.
            if not getattr(model.generation_config, "no_timestamps_token_id", None):
                base = os.getenv("ASR_BASE") or ("openai/whisper-large-v3" if "large" in MODEL
                                                 else "openai/whisper-medium" if "medium" in MODEL
                                                 else "openai/whisper-small")
                try: model.generation_config = GenerationConfig.from_pretrained(base)
                except Exception: pass
            try: proc = AutoProcessor.from_pretrained(MODEL)
            except Exception: proc = AutoProcessor.from_pretrained("openai/whisper-small")
            _m["m"] = pipeline("automatic-speech-recognition", model=model, tokenizer=proc.tokenizer,
                               feature_extractor=proc.feature_extractor, device=-1)
        else:
            from faster_whisper import WhisperModel
            _m["m"] = WhisperModel(MODEL, device="cpu", compute_type="int8")
    return _m["m"]


def group_spans(spans, lo=6.0, hi=24.0, cap=28.0):
    """Звучащие куски склеиваются в отрезки по 6–24 секунды: модели так удобнее, а строки выходят длиной с фразу."""
    out = []
    for a, b in spans:
        if out and out[-1][1] - out[-1][0] < lo and b - out[-1][0] <= hi: out[-1][1] = b
        else: out.append([a, b])
    res = []
    for a, b in out:
        while b - a > cap: res.append((a, a + cap)); a += cap
        res.append((a, b))
    return res


def transcribe_hf(m, x, sr, on_progress=None):
    """Дообученная модель с Hugging Face (пишет башкирской кириллицей).
    Запись режется по паузам на короткие отрезки, каждый расшифровывается отдельно:
    время каждой строки известно заранее, а на странице виден ход работы."""
    groups = group_spans(speech_spans(x, sr)) or [(0.0, len(x) / sr)]
    kw = {"language": LANG, "task": "transcribe"} if LANG else {}
    out = []
    for n, (a, b) in enumerate(groups):
        seg = {"raw": x[int(a * sr):int(b * sr)], "sampling_rate": sr}
        try:
            r = m(dict(seg), generate_kwargs=kw) if kw else m(dict(seg))
        except (TypeError, ValueError):
            kw = {}                                        # у модели язык зашит — больше его не передаём
            r = m(dict(seg))
        text = " ".join((r.get("text") or "").split())
        parts = sentences(text) or ([text] if text else [])
        total = sum(len(p) for p in parts) or 1
        pos = a
        for p in parts:                                    # несколько предложений в отрезке — делим время по длине
            share = (b - a) * len(p) / total
            out.append((int(pos), max(int(pos) + 1, int(pos + share)), p)); pos += share
        if on_progress: on_progress(min(0.99, (n + 1) / len(groups)))
    return out


def explain(ex):
    """Понятное объяснение вместо английской ошибки библиотеки."""
    s = f"{type(ex).__name__}: {ex}".strip()
    low = s.lower()
    if any(w in low for w in ("connection", "timeout", "resolve", "network", "ssl", "proxy", "max retries", "getaddrinfo")):
        return "не удалось скачать модель — нет связи с интернетом или её закрывает брандмауэр", s
    if any(w in low for w in ("404", "not found", "repository", "gated", "401", "403", "invalid model", "expected one of")):
        return f"модель «{MODEL}» не найдена — проверьте значение ASR_MODEL в файле .env", s
    if "memory" in low or "alloc" in low:
        return "не хватило оперативной памяти — возьмите модель поменьше: ASR_MODEL=tiny", s
    if "dll" in low or "library" in low or "symbol" in low:
        return "библиотеке распознавания не хватает системных файлов — обычно помогает установка Microsoft Visual C++ Redistributable", s
    if "language" in low:
        return f"модель не знает язык «{LANG}» — поменяйте ASR_LANG в .env", s
    return "распознавание не справилось с этой записью", s


def check():
    """Что именно не так с распознаванием: показывается в интерфейсе и в asr_check.py."""
    if not available(): return {"ok": False, "why": "Пакет распознавания не установлен — запустите install_asr.bat"}
    try:
        _load()
        return {"ok": True, "model": MODEL, "lang": LANG}
    except Exception as ex:
        why, raw = explain(ex)
        return {"ok": False, "why": f"Модель «{MODEL}»: {why}", "raw": raw}


def transcribe(path, on_progress=None):
    with _lock:
        m = _load()
        # Звук читаем сами: встроенный в faster-whisper декодер ломается на новых версиях PyAV
        # (open() got an unexpected keyword argument 'metadata_errors'), а модель принимает готовый массив.
        x, sr = read_pcm(path, 16000)
        dur = len(x) / sr
        if dur > MAX_MINUTES * 60:
            raise RuntimeError(f"Запись длиннее {MAX_MINUTES} минут — разделите её на части")
        if is_hf():
            rows = transcribe_hf(m, x, 16000, on_progress)
            return [(a, (rows[i + 1][0] if i + 1 < len(rows) else b), t) for i, (a, b, t) in enumerate(rows)]
        segs, info = m.transcribe(x, language=LANG or None, vad_filter=True, beam_size=5,
                                  condition_on_previous_text=False)
        out, dur = [], max(1.0, info.duration)
        for s in segs:
            t = (s.text or "").strip()
            if t: out.append((int(s.start), max(int(s.start) + 1, int(s.end)), t))
            if on_progress: on_progress(min(0.99, s.end / dur))
        # границы встык, чтобы при прослушивании ничего не обрезалось
        return [(a, (out[i + 1][0] if i + 1 < len(out) else b), t) for i, (a, b, t) in enumerate(out)]


def alphabet_note(text, mode):
    """Многоязычная модель не знает башкирского алфавита и пишет латиницей.
    Если так вышло — честно предупреждаем и показываем, как получить настоящий текст."""
    if mode == "pauses" or LANG not in ("ba", "tt", "kk", "ru"): return ""
    lat = sum(c.isalpha() and c.isascii() for c in text)
    cyr = sum(c.isalpha() and not c.isascii() for c in text)
    if lat > cyr:
        return ("Модель записала речь латиницей — она плохо знает башкирский алфавит, и такие "
                "строки в задания не попадут. Отметки времени при этом верные. Если расшифровка "
                "есть — вставьте её и нажмите «Разложить мой текст по паузам». Если текста нет — "
                "поставьте башкирскую модель (install_asr_ba.bat), она пишет кириллицей.")
    return ""


def as_lines(rows):
    """Строки для карточки нарезки: «мм:сс текст» (часы — если запись длинная)."""
    def tc(t):
        h, m, s = t // 3600, t // 60 % 60, t % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    return "\n".join(f"{tc(a)} {t}" for a, _b, t in rows)
