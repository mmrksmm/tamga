"""Прячет из заданий уже загруженные плохие пары (обрывки, сбитое выравнивание).

    cd app && python clean_fragments.py           # показать, что будет скрыто
    cd app && python clean_fragments.py --apply   # скрыть

Фрагменты не удаляются: они получают active=0, поэтому в новых заданиях не появятся,
а уже собранные по ним переводы и статистика остаются на месте.
"""
import sys, envload  # noqa
from models import SessionLocal, Fragment, AutoTr
from quality import bad_pair

apply = "--apply" in sys.argv
s = SessionLocal()
auto = {}
for a in s.query(AutoTr): auto.setdefault(a.fragment_id, []).append(a)
bad = []
for f in s.query(Fragment).filter_by(active=True):
    why = ""
    for a in auto.get(f.id, []):
        why = bad_pair(f.text_ba, a.text)
        if why: break
    if not why and not auto.get(f.id) and len(f.text_ba.split()) < 2: why = "одно слово без перевода"
    if why: bad.append((f, why))

for f, why in bad[:40]: print(f"[{why}] {f.text_ba[:60]} | {(auto.get(f.id) or [None])[0].text[:60] if auto.get(f.id) else ''}")
print(f"\nНайдено плохих фрагментов: {len(bad)} из {s.query(Fragment).filter_by(active=True).count()}")
if apply:
    for f, _ in bad: f.active = False
    s.commit(); print("Скрыто. Обновите страницу сайта.")
else:
    print("Это предварительный просмотр. Чтобы скрыть их, запустите: python clean_fragments.py --apply")
