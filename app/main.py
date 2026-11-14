import envload  # noqa: F401  (должен быть первым)
import asyncio, logging, os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from models import Base, engine, ensure_columns
from security import limiter, ip_of
from seed import seed
from api import router
from extra import router as extra_router
from links import router as links_router
from learn import router as learn_router

BASE = Path(__file__).resolve().parent
Base.metadata.create_all(engine); ensure_columns()
seed()

def auto_import():
    """AUTO_IMPORT=kk,alt,ar,sah,zh и AUTO_IMPORT_SCHOOLS=1 — при старте сайта самому загрузить датасеты и школы
    (то же, что import_dataset.bat / import_schools.bat). Уже загруженное пропускается. demo.bat делает это заранее, до запуска сайта."""
    import subprocess, sys, threading
    langs = [l.strip() for l in os.getenv("AUTO_IMPORT", "").split(",") if l.strip()]
    schools = os.getenv("AUTO_IMPORT_SCHOOLS") == "1"
    if not langs and not schools: return
    root = BASE.parent
    def run():
        from models import SessionLocal, Fragment, School
        log = logging.getLogger("tamga")
        with SessionLocal() as s:
            todo = [l for l in langs if not s.query(Fragment.id).filter(Fragment.chapter == f"разговорник ba-ru-{l}").first()]
            need_schools = schools and s.query(School).count() < 100
        for l in todo:
            log.info("Автоимпорт датасета %s", l)
            subprocess.run([sys.executable, str(root / "import_hf.py"), "--lang", l], cwd=BASE)
        if need_schools:
            log.info("Автоимпорт школ")
            subprocess.run([sys.executable, str(root / "import_schools.py")], cwd=BASE)
    threading.Thread(target=run, daemon=True).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """RUN_BOT=1 — запускать Telegram-бота прямо внутри сайта.
    Нужно для бесплатных хостингов, где можно держать только один процесс.
    На своём сервере бот запускается отдельно (docker compose, start_bot.bat)."""
    task = None
    try: auto_import()
    except Exception: logging.getLogger("tamga").exception("автоимпорт не запустился")
    token = os.getenv("TELEGRAM_TOKEN", "")
    if os.getenv("RUN_BOT") == "1" and ":" in token:   # токен BotFather всегда вида 123456:ABC… — заглушка не пройдёт
        import bot as tgbot
        task = asyncio.create_task(tgbot.main())
        logging.getLogger("tamga").info("Telegram-бот запущен внутри сайта")
    elif os.getenv("RUN_BOT") == "1":
        logging.getLogger("tamga").warning("TELEGRAM_TOKEN не заполнен в .env — сайт работает без Telegram-бота")
    yield
    if task:
        task.cancel()
        try: await task
        except (asyncio.CancelledError, Exception): pass

app = FastAPI(title="Тамға — API", version="1.0.0", lifespan=lifespan,
              description="Образовательная платформа и база проверенных переводов")

CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "script-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; frame-ancestors 'none'")

@app.middleware("http")
async def protect(request: Request, call_next):
    if request.url.path.startswith("/api"):
        try: limiter.hit("all:" + ip_of(request), 300, 60)
        except HTTPException as e: return JSONResponse({"detail": e.detail}, status_code=429)
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
                      "Content-Security-Policy": CSP, "Cache-Control": "no-store" if request.url.path.startswith("/api") else "no-cache"})
    return r

FIELDS = {"name": "Имя", "email": "Почта", "password": "Пароль", "code": "Код", "text": "Текст", "grade": "Класс", "letter": "Буква",
          "school_id": "Школа", "city": "Город", "translation": "Перевод", "kind": "Действие", "pair": "Языковая пара", "source_doc": "Источник"}

def ru_msg(e):
    f = FIELDS.get(str(e["loc"][-1]), str(e["loc"][-1])); ty, c = e["type"], e.get("ctx", {})
    if ty == "missing": return f"Заполните поле «{f}»"
    if ty == "string_too_short": return f"Поле «{f}» слишком короткое" + (f" (минимум {c['min_length']} симв.)" if "min_length" in c else "")
    if ty == "string_too_long": return f"Поле «{f}» слишком длинное (максимум {c.get('max_length', '')} симв.)"
    if ty == "string_pattern_mismatch": return "Введите корректный адрес почты, например name@mail.ru" if f == "Почта" else f"Поле «{f}» заполнено неверно"
    if ty in ("greater_than_equal", "less_than_equal", "greater_than", "less_than"): return f"Поле «{f}»: значение вне допустимого диапазона"
    return f"Поле «{f}» заполнено неверно"

@app.exception_handler(RequestValidationError)
async def on_validation(request, exc): return JSONResponse({"detail": ru_msg(exc.errors()[0])}, status_code=422)

RU_HTTP = {404: "Страница или объект не найден", 405: "Этот запрос не поддерживается", 401: "Требуется авторизация", 403: "Недостаточно прав", 429: "Слишком много запросов, подождите немного"}
@app.exception_handler(StarletteHTTPException)
async def on_http(request, exc):
    d = exc.detail if isinstance(exc.detail, str) and any("а" <= ch.lower() <= "я" for ch in exc.detail) else RU_HTTP.get(exc.status_code, "Что-то пошло не так")
    return JSONResponse({"detail": d}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def on_error(request, exc): return JSONResponse({"detail": "Внутренняя ошибка сервера. Попробуйте ещё раз позже"}, status_code=500)

app.include_router(extra_router)
app.include_router(links_router)
app.include_router(learn_router)
app.include_router(router)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

@app.get("/", include_in_schema=False)
def home(): return FileResponse(BASE / "static" / "index.html")
