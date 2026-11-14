"""Импорт параллельных фраз из датасета Фонда сохранения и развития башкирского языка:
bashkorttele/trilingual-parallel-phrasebooks-bgpu (CC BY 4.0).

    cd app && python ../import_hf.py --lang kk            # alt, ar, kk, sah, zh
    cd app && python ../import_hf.py --lang kk --file data-ba-ru-kk.jsonl   # из скачанного файла

Каждая фраза становится фрагментом (text_ba) с координатами источника: русский текст — автоперевод пары ba-ru,
третий язык — автоперевод пары ba-<lang>. «Заведомо ошибочный» вариант строится правилом: перевод другой фразы.
"""
import argparse, json, random, sys, urllib.request, urllib.error
sys.path.insert(0, ".")
import envload  # noqa
from models import SessionLocal, Base, engine, Fragment, AutoTr
from quality import bad_pair

URL = "https://huggingface.co/datasets/bashkorttele/trilingual-parallel-phrasebooks-bgpu/resolve/main/data/data-ba-ru-{}.jsonl"
SRC = "Разговорник БГПУ им. М. Акмуллы · Фонд сохранения и развития башкирского языка (CC BY 4.0)"

ap = argparse.ArgumentParser()
ap.add_argument("--lang", required=True, choices=["alt", "ar", "kk", "sah", "zh"])
ap.add_argument("--limit", type=int, default=5000)
ap.add_argument("--file")
a = ap.parse_args()

if a.file:
    raw = open(a.file, encoding="utf-8").read()
else:
    try:
        # скачивание с процентами, чтобы было видно, сколько ждать
        _st = {"p": -1}
        def _hook(blocks, bs, total):
            if total > 0:
                p = min(100, blocks * bs * 100 // total)
                if p != _st["p"]:
                    _st["p"] = p
                    print(f"\r  скачивание data-ba-ru-{a.lang}.jsonl: {p}%", end="", flush=True)
        import tempfile
        _tmp = tempfile.mktemp(suffix=".jsonl")
        urllib.request.urlretrieve(URL.format(a.lang), _tmp, _hook)
        print()
        raw = open(_tmp, encoding="utf-8").read()
    except urllib.error.URLError as e:
        sys.exit(f"Не удалось скачать датасет ({e}). Скачайте файл data-ba-ru-{a.lang}.jsonl вручную "
                 f"со страницы датасета и запустите с параметром --file.")

rows = [json.loads(l) for l in raw.splitlines() if l.strip()]
rows = [r for r in rows if 4 <= len(r.get("text_ba", "")) <= 220 and r.get("text_ru", "").strip() and r.get("text_other", "").strip()]
# отсев обрывков и строк со сбитым выравниванием (датасет выравнивали не построчно)
good, skipped = [], {}
for r in rows:
    why = bad_pair(r["text_ba"], r["text_ru"]) or bad_pair(r["text_ba"], r["text_other"])
    if why: skipped[why] = skipped.get(why, 0) + 1
    else: good.append(r)
rows = good
random.seed(1)
rows = rows[:a.limit]
ru_pool = [r["text_ru"] for r in rows]
ot_pool = [r["text_other"] for r in rows]

def wrong(pool, own):
    for _ in range(30):
        w = random.choice(pool)
        if w.strip().lower() != own.strip().lower():
            return w
    return ""

Base.metadata.create_all(engine)
s = SessionLocal()
known = {(f.text_ba, f.source_doc): f for f in s.query(Fragment).filter_by(source_doc=SRC)}
have = {(t.fragment_id, t.pair) for t in s.query(AutoTr.fragment_id, AutoTr.pair)}
added = 0
_n = len(rows)
for _i, r in enumerate(rows, 1):
    if _i % 250 == 0 or _i == _n:
        print(f"\r  запись в базу: {100 * _i // max(_n, 1)}% ({_i}/{_n})", end="", flush=True)
    tail = r.get("id", "").rsplit("-", 1)[-1]
    pos = int(tail) if tail.isdigit() else 0
    f = known.get((r["text_ba"], SRC))
    if not f:
        f = Fragment(text_ba=r["text_ba"], source_doc=SRC, chapter=f"разговорник ba-ru-{a.lang}", position=pos)
        s.add(f); s.flush(); known[(r["text_ba"], SRC)] = f; added += 1
    for pair, txt, pool in (("ba-ru", r["text_ru"], ru_pool), (f"ba-{a.lang}", r["text_other"], ot_pool)):
        if (f.id, pair) not in have:
            s.add(AutoTr(fragment_id=f.id, pair=pair, text=txt[:600], wrong=wrong(pool, txt)[:600]))
            have.add((f.id, pair))
s.commit()
print("\nГотово. Новых фрагментов:", added)
if skipped: print("Пропущено плохих строк:", sum(skipped.values()), "—", ", ".join(f"{k}: {v}" for k, v in sorted(skipped.items(), key=lambda x: -x[1])))
