"""Собирает готовую озвучку фрагментов в папку app/voice, чтобы она работала на сервере без модели.

    cd app && python voice_pack.py          # учебный корпус (то, что есть на новом сайте)
    cd app && python voice_pack.py --all    # все активные фрагменты из локальной базы

Запускается на компьютере, где установлена озвучка (install_tts.bat). Папку app/voice
после этого нужно загрузить в репозиторий — сервер начнёт отдавать эти файлы.
"""
import shutil, sys, envload  # noqa
import tts
from models import SessionLocal, Fragment
from seed import DOC

if not tts.available():
    print("Озвучка не установлена: сначала запустите install_tts.bat"); raise SystemExit(1)
s = SessionLocal()
q = s.query(Fragment).filter_by(active=True)
if "--all" not in sys.argv: q = q.filter_by(source_doc=DOC)
frags = q.all()
tts.PACK.mkdir(exist_ok=True)
done = 0
for i, f in enumerate(frags, 1):
    _, name = tts._name(f.text_ba)
    if not (tts.PACK / name).exists():
        p = tts.synth(f.text_ba)
        if not p: print(f"  не получилось: {f.text_ba[:50]}"); continue
        shutil.copyfile(p, tts.PACK / name)
    done += 1
    print(f"{i}/{len(frags)}  {f.text_ba[:60]}")
size = sum(p.stat().st_size for p in tts.PACK.glob("*.wav")) / 1e6
print(f"\nГотово: {done} файлов, {size:.1f} МБ в папке app\\voice. Загрузите её в репозиторий.")
