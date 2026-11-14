"""Проверка распознавания речи: показывает, всё ли готово, и если нет — в чём дело."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asr

if "--model" in sys.argv:                      # проверить конкретную модель, не трогая .env
    asr.MODEL = sys.argv[sys.argv.index("--model") + 1]
print(f"Модель: {asr.MODEL}, язык: {asr.LANG}")
if not asr.available():
    print("Нужные пакеты не установлены:")
    print("  install_asr.bat     — быстрая многоязычная модель (пишет латиницей на башкирском)")
    print("  install_asr_ba.bat  — башкирская модель, пишет кириллицей")
    raise SystemExit(1)
print("Проверяю модель (первая загрузка скачивает от 0.5 до 1.5 ГБ, это несколько минут)...")
t = time.time()
r = asr.check()
if r["ok"]:
    print(f"Готово за {round(time.time() - t)} с. Кнопка «Расшифровать запись» будет работать.")
else:
    print("Не получилось:", r["why"])
    if r.get("raw"): print("Подробности для разбирательства:", r["raw"])
    print("\nЕсли дело в интернете — разметку по паузам это не затрагивает:")
    print("вставьте текст, нажмите «Разложить мой текст по паузам», модель для этого не нужна.")
    raise SystemExit(1)
