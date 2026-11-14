"""Проверка серверной озвучки: python tts_check.py — создаст файл tts_test.wav и откроет его."""
import os, sys, envload  # noqa
import tts
if not tts.available(): sys.exit("Озвучка не установлена: запустите install_tts.bat")
print("Скачиваю модель (первый раз ~150 МБ) и озвучиваю фразу…")
p = tts.synth("Һаумыһығыҙ! Беҙ башҡортса һөйләшәбеҙ.")
if not p: sys.exit("Не получилось — пришлите текст ошибки выше.")
out = os.path.abspath("tts_test.wav"); open(out, "wb").write(p.read_bytes())
print("Готово:", out)
if os.name == "nt": os.startfile(out)
