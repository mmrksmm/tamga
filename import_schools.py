"""Загрузка списка школ Башкортостана с https://shkola.city/ba.

    cd app && python ../import_schools.py

Сайт показывает по 10 школ и догружает остальные; скрипт перебирает ?page=2,3… и останавливается,
когда новых школ нет. Между запросами — пауза, чтобы не нагружать сайт. Повторный запуск безопасен: дубликаты пропускаются.
"""
import re, sys, time, requests
from bs4 import BeautifulSoup
sys.path.insert(0, ".")
import envload  # noqa
from models import SessionLocal, School, Base, engine

BASE = "https://shkola.city"
H = {"User-Agent": "Mozilla/5.0 (Tamga school import)"}
SKIP = ("colleges", "nachalnye", "litsei", "gimnazii", "uchilisha", "shkolyinternaty")

def get(u):
    return BeautifulSoup(requests.get(u, headers=H, timeout=30).text, "html.parser")

def tidy(name):
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"№\s*(\d+)", r"№ \1", name)
    return name[:160]

def places(soup):
    out = {}
    for a in soup.select('a[href*="/ba/places/"]'):
        n = a.get_text(" ", strip=True)
        if n and not n.startswith("Подробнее") and not re.fullmatch(r"[\d\s]+", n):
            out[a["href"]] = tidy(n)
    return out

def pages(url):
    seen = {}
    for p in range(1, 60):
        new = places(get(url if p == 1 else f"{url}?page={p}"))
        if not set(new) - set(seen):
            break
        seen.update(new); time.sleep(1)
    return seen

Base.metadata.create_all(engine)
s = SessionLocal()
# убираем обрезанные названия («…школа №») из прошлых неудачных запусков, если к ним никто не привязан
from models import User
used = {i for (i,) in s.query(User.school_id).filter(User.school_id.isnot(None))}
for sc in s.query(School).filter(School.name.like("%№")):
    if sc.id not in used: s.delete(sc)
s.commit()
known = {(c, n.lower()) for c, n in s.query(School.city, School.name)}
total = 0
# сначала собираем список городов и районов, чтобы показывать проценты выполнения
towns = []
for a in get(BASE + "/ba").select('a[href^="https://shkola.city/ba/"]'):
    m = re.match(r"(.+?)\s+\d+$", a.get_text(" ", strip=True))
    if not m or a["href"].rstrip("/").split("/")[-1] in SKIP:
        continue
    towns.append((m.group(1) + (" район" if m.group(1).endswith("ский") else ""), a["href"]))
for i, (city, href) in enumerate(towns, 1):
    try:
        names = pages(href).values()
    except requests.RequestException as e:
        print(f"  {100 * i // len(towns)}% ({i}/{len(towns)})", city, "пропущен:", e); continue
    for name in names:
        if name and (city, name.lower()) not in known:
            s.add(School(city=city, name=name)); known.add((city, name.lower())); total += 1
    s.commit()
    print(f"  {100 * i // len(towns)}% ({i}/{len(towns)})", city, "ok", flush=True)
print("Добавлено школ:", total)
