"""Проверка Telegram-бота без сети: запросы к Telegram подменены, бот работает с настоящей базой."""
import os, sys, re, asyncio, tempfile, datetime as dt
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "b.db"))
os.environ.setdefault("TELEGRAM_TOKEN", "1:test")
os.environ["PLANT_RATE"] = "0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.types import Update, Message, Chat, User as TUser, CallbackQuery
from models import Base, engine, SessionLocal, ClassInvite, User, School
from seed import seed
Base.metadata.create_all(engine); seed()
import bot as B

SENT = []
class FakeTelegram(BaseSession):
    async def make_request(self, bot, method, timeout=None):
        SENT.append((getattr(method, "text", None) or "", getattr(method, "reply_markup", None)))
        if "Message" in str(method.__returning__):
            return Message(message_id=len(SENT), date=dt.datetime.now(), chat=Chat(id=77, type="private"), text="x")
        return True
    async def close(self): pass
    async def stream_content(self, *a, **k): yield b""

bot = Bot("1:test", session=FakeTelegram())
U = TUser(id=77, is_bot=False, first_name="Y", language_code="ru")
n = [0]
def msg(t):
    n[0] += 1; return Update(update_id=n[0], message=Message(message_id=n[0], date=dt.datetime.now(), chat=Chat(id=77, type="private"), from_user=U, text=t))
def cb(d):
    n[0] += 1; return Update(update_id=n[0], callback_query=CallbackQuery(id=str(n[0]), from_user=U, chat_instance="c", data=d,
                             message=Message(message_id=1, date=dt.datetime.now(), chat=Chat(id=77, type="private"), from_user=U, text="q")))
def buttons(): mk = SENT[-1][1]; return [b.callback_data for row in mk.inline_keyboard for b in row] if mk is not None and hasattr(mk, "inline_keyboard") else []
async def go(u): await B.dp.feed_update(bot, u)

def test_full_dialog():
    s = SessionLocal(); sc = s.query(School).first(); t = s.query(User).filter_by(role="teacher").first()
    s.merge(ClassInvite(code="BOT777", teacher_id=t.id, school_id=sc.id, grade=7, letter="Б")); s.commit(); s.close()
    async def run():
        await go(msg("/start")); assert "Как вас зовут" in SENT[-1][0]
        await go(msg("Ученик Бота")); assert buttons() == ["skipclass"]
        await go(msg("bot777")); assert "7Б" in SENT[-2][0]
        for i in range(5):
            await go(msg("✍️ Задание дня") if i == 0 else cb("next"))
            b = buttons()
            if b and b[0].startswith("ok:"):
                if i == 1: await go(cb("fix:" + b[0][3:])); await go(msg("исправленный перевод"))
                else: await go(cb(b[0]))
            else: await go(msg("свой перевод"))
            # очки теперь приходят после подтверждения другими, поэтому ответ подтверждается словами
            assert any(w in SENT[-1][0] for w in ("XP", "Ответ принят", "Ловушка", "ошибку"))
        assert "Дневная норма выполнена" in SENT[-1][0] and buttons() == ["more"]
        await go(cb("more"))
        b = buttons()   # фрагмент с автопереводом даёт кнопки; фрагмент без него просит написать перевод словами
        assert (b and b[0].startswith(("ok:", "say:"))) or "перевод" in SENT[-1][0]
        await go(msg("/cancel"))
        await go(msg("📊 Прогресс")); assert "Серия: 1" in SENT[-1][0]
        await go(msg("🏆 Рейтинг")); assert "Ученик Бота" in SENT[-1][0]
        await go(msg("⚙️ Настройки")); await go(cb("s:site"))
        return re.search(r"/#/tg/(\w+)", SENT[-1][0]).group(1)
    code = asyncio.run(run())
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.post("/api/tg/login", json={"code": code})
    assert r.status_code == 200 and r.json()["user"]["class_name"] == "7Б"
    assert c.post("/api/tg/login", json={"code": code}).status_code == 400   # ссылка одноразовая

def test_link_site_account_and_class_code():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    h = {"Authorization": "Bearer " + c.post("/api/login", json={"email": "student@demo.ru", "password": "demo123"}).json()["token"]}
    code = c.post("/api/tg/link-code", headers=h).json()["code"]
    U2 = TUser(id=78, is_bot=False, first_name="Z")
    upd = Update(update_id=999, message=Message(message_id=999, date=dt.datetime.now(), chat=Chat(id=78, type="private"), from_user=U2, text=f"/start link_{code}"))
    asyncio.run(B.dp.feed_update(bot, upd))
    assert "Алина" in SENT[-1][0]
    assert c.get("/api/tg/status", headers=h).json()["linked"]
    assert c.post("/api/me/class-code", json={"code": "nope"}, headers=h).status_code == 400
    assert c.post("/api/me/class-code", json={"code": "bot777"}, headers=h).json()["class_name"] == "7Б"
