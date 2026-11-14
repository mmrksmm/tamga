"""Telegram-бот Тамги: регистрация, ежедневные задания, прогресс, рейтинг, напоминания.

Запуск (из папки app):  python bot.py
Нужны переменные в .env: TELEGRAM_TOKEN (от @BotFather), BOT_USERNAME, PUBLIC_URL (адрес сайта).
Бот работает с той же базой, что и сайт: задания, ответы, XP и серия общие.
Состояние диалога (FSM) хранится в таблице tg_users, поэтому переживает перезапуск бота.
"""
import asyncio, html, json, logging, os, random, sys, datetime as dt
from zoneinfo import ZoneInfo
import envload  # noqa: F401  (должен быть первым)
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (Message, CallbackQuery, BotCommand, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton)
from fastapi import HTTPException
from models import Base, engine, ensure_columns, SessionLocal, User, TgUser, Answer, Fragment, AutoTr
from seed import seed
import extra, links, tts
from api import live_streak

log = logging.getLogger("tamga.bot")
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
SITE = os.getenv("PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
TZ = ZoneInfo(os.getenv("BOT_TZ", "Asia/Yekaterinburg"))       # время Уфы
REMIND_FROM = int(os.getenv("REMIND_FROM", "8"))               # раньше этого часа напоминания не шлём (0 — слать и ночью)
GOAL = extra.DAILY

# ---------- тексты бота: [русский, башкирский] ----------
TX = {
"hello": ["👋 Сәләм! Я бот <b>Тамға</b> — башкирской языковой школы.\n\nКаждый день я присылаю 5 фраз на башкирском с автопереводом: подтвердите его или исправьте. Из ваших ответов собирается база проверенных переводов, а вы получаете XP и огонёк серии 🔥\n\nКак вас зовут? Напишите имя.",
          "👋 Сәләм! Мин — <b>Тамға</b> боты, башҡорт теле мәктәбе.\n\nКөн һайын мин автотәржемәһе менән 5 башҡортса һөйләм ебәрәм: уны раҫлағыҙ йәки төҙәтегеҙ. Яуаптарығыҙҙан тикшерелгән тәржемәләр базаһы йыйыла, ә һеҙ XP һәм рәттәнлек утын алаһығыҙ 🔥\n\nИсемегеҙ нисек? Яҙығыҙ."],
"bad_name": ["Имя должно быть от 1 до 40 символов. Напишите ещё раз.", "Исем 1-ҙән 40 символға тиклем булырға тейеш. Ҡабат яҙығыҙ."],
"ask_class": ["Приятно познакомиться, {name}! Если учитель дал вам <b>код класса</b>, пришлите его. Если нет — нажмите «Пропустить».",
              "Танышыуыбыҙға шатмын, {name}! Уҡытыусы <b>класс кодын</b> биргән булһа, ебәрегеҙ. Юҡ икән — «Үтеп китергә» төймәһенә баҫығыҙ."],
"skip": ["Пропустить", "Үтеп китергә"],
"bad_class": ["Такого кода нет. Проверьте его у учителя или нажмите «Пропустить».", "Бындай код юҡ. Уҡытыусынан тикшерегеҙ йәки «Үтеп китергә» төймәһенә баҫығыҙ."],
"class_ok": ["Вы добавлены в класс {cls}, {school}.", "Һеҙ {school}, {cls} класына өҫтәлдегеҙ."],
"ready": ["Готово! Нажмите «✍️ Задание дня», чтобы начать.", "Әҙер! Башлау өсөн «✍️ Көн бурысы» төймәһенә баҫығыҙ."],
"welcome_back": ["С возвращением, {name}! 🔥 Серия: {streak} дн. · сегодня {today}/{goal}", "Яңынан хуш киләһегеҙ, {name}! 🔥 Рәттән: {streak} көн · бөгөн {today}/{goal}"],
"linked": ["✅ Telegram привязан к аккаунту <b>{name}</b>. Прогресс на сайте и в боте теперь общий.", "✅ Telegram <b>{name}</b> аккаунтына бәйләнде. Сайттағы һәм боттағы уңыштар хәҙер уртаҡ."],
"link_bad": ["Ссылка для привязки устарела. Получите новую на сайте: Настройки → Telegram.", "Бәйләү һылтанмаһы иҫкергән. Сайтта яңыһын алығыҙ: Көйләүҙәр → Telegram."],
"m_task": ["✍️ Задание дня", "✍️ Көн бурысы"], "m_stats": ["📊 Прогресс", "📊 Уңыштар"], "m_top": ["🏆 Рейтинг", "🏆 Рейтинг"], "m_set": ["⚙️ Настройки", "⚙️ Көйләүҙәр"],
"auto": ["🤖 Автоперевод — проверьте его:", "🤖 Автотәржемә — тикшерегеҙ:"],
"write_own": ["✏️ Автоперевода нет — напишите свой перевод сообщением.", "✏️ Автотәржемә юҡ — үҙ тәржемәгеҙҙе хәбәр итеп яҙығыҙ."],
"b_ok": ["✔ Верно", "✔ Дөрөҫ"], "b_fix": ["✎ Исправить", "✎ Төҙәтергә"], "b_say": ["🔊 Послушать", "🔊 Тыңларға"], "b_next": ["Дальше ➜", "Артабан ➜"], "b_more": ["✍️ Продолжить переводить", "✍️ Тәржемәне дауам итергә"],
"send_fix": ["Пришлите правильный перевод одним сообщением.\nСейчас: <i>{auto}</i>", "Дөрөҫ тәржемәне бер хәбәр менән ебәрегеҙ.\nХәҙер: <i>{auto}</i>"],
"xp": ["✅ +{xp} XP", "✅ +{xp} XP"],
"accepted": ["✅ Ответ принят. Очки придут, когда ваш вариант подтвердят другие участники.", "✅ Яуап ҡабул ителде. Башҡа ҡатнашыусылар раҫлағас, баллдар килер."],
"trap": ["⚠️ Ловушка! Это был заведомо неверный вариант.\nПравильно: <b>{right}</b>", "⚠️ Тоҙаҡ! Был махсус яңылыш вариант ине.\nДөрөҫө: <b>{right}</b>"],
"fixed": ["🔍 Вы нашли подставную ошибку! +{xp} XP", "🔍 Һеҙ махсус хатаны таптығыҙ! +{xp} XP"],
"fixed0": ["🔍 Вы нашли подставную ошибку!", "🔍 Һеҙ махсус хатаны таптығыҙ!"],
"confirmed": ["🎉 Перевод подтверждён сообществом и попал в базу", "🎉 Тәржемә берләшмә тарафынан раҫланды һәм базаға инде"],
"expert": ["⚖️ Мнения разошлись — случай передан экспертам", "⚖️ Фекерҙәр айырылды — мәсьәлә белгестәргә ебәрелде"],
"goal_now": ["🔥 <b>Дневная норма выполнена — огонёк горит!</b>", "🔥 <b>Көнлөк норма үтәлде — ут яна!</b>"],
"flame_xp": ["🔥 +{xp} XP за зажжённый огонёк!", "🔥 Ҡабынған ут өсөн +{xp} XP!"],
"done_title": ["🔥 На сегодня норма выполнена ({today}/{goal}).\nМожно отдохнуть — или перевести ещё немного.", "🔥 Бөгөнгө норма үтәлде ({today}/{goal}).\nЯл итергә йәки тағы бер аҙ тәржемә итергә мөмкин."],
"finish": ["Молодец! 🎉 +{xp} XP за подход · найдено ошибок: {fixes}", "Афарин! 🎉 +{xp} XP · табылған хаталар: {fixes}"],
"no_more": ["Новые фрагменты для этой пары закончились. Выберите другую пару в настройках или загляните позже.", "Был пар өсөн яңы өҙөктәр бөттө. Көйләүҙәрҙә башҡа пар һайлағыҙ йәки һуңыраҡ килегеҙ."],
"stats": ["📊 <b>{name}</b>\n⭐ Уровень {level} · {xp} XP\n🔥 Серия: {streak} дн.\n✍️ Сегодня: {today}/{goal}\n📖 Слов встречено: {vocab}\n🔍 Найдено подставных ошибок: {fixes}\n🎯 Точность: {acc}%{school}",
          "📊 <b>{name}</b>\n⭐ Кимәл {level} · {xp} XP\n🔥 Рәттән: {streak} көн\n✍️ Бөгөн: {today}/{goal}\n📖 Осраған һүҙҙәр: {vocab}\n🔍 Табылған махсус хаталар: {fixes}\n🎯 Теүәллек: {acc}%{school}"],
"top": ["🏆 <b>Рейтинг за неделю</b> (баллы)", "🏆 <b>Аҙналыҡ рейтинг</b> (баллар)"], "top_empty": ["За эту неделю пока никто не переводил.", "Был аҙнала әлегә бер кем дә тәржемә итмәгән."],
"settings": ["⚙️ <b>Настройки</b>\nЯзыковая пара: {pair}\nНапоминания в течение дня: {remind}", "⚙️ <b>Көйләүҙәр</b>\nТел парлығы: {pair}\nКөн дауамында иҫкәртеүҙәр: {remind}"],
"on": ["вкл", "ҡабыҙылған"], "off": ["выкл", "һүндерелгән"],
"s_pair": ["🔁 Языковая пара", "🔁 Тел парлығы"], "s_lang": ["🌐 Башҡортса", "🌐 Русский"], "s_rem": ["🔔 Напоминания вкл/выкл", "🔔 Иҫкәртеүҙәр ҡабыҙ/һүндер"], "s_site": ["🔑 Войти на сайт", "🔑 Сайтҡа инеү"],
"s_class": ["🏫 Ввести код класса", "🏫 Класс кодын индерергә"],
"pick_pair": ["Выберите языковую пару:", "Тел парлығын һайлағыҙ:"], "pair_ok": ["Языковая пара: {pair}", "Тел парлығы: {pair}"],
"site_link": ["Ссылка для входа на сайт (действует 10 минут, одноразовая):\n{url}", "Сайтҡа инеү һылтанмаһы (10 минут эшләй, бер тапҡыр ғына):\n{url}"],
"send_class": ["Пришлите код класса от учителя.", "Уҡытыусынан алынған класс кодын ебәрегеҙ."],
"cancel": ["Действие отменено. Главное меню 👇", "Ғәмәл туҡтатылды. Төп меню 👇"],
"no_voice": ["Озвучка пока не включена на сервере.", "Серверҙа тауыш менән уҡыу әлегә ҡабыҙылмаған."],
"help": ["Команды:\n/task — задание дня\n/stats — мой прогресс\n/top — рейтинг\n/settings — настройки\n/cancel — отменить текущее действие\n\nСайт: {site}",
         "Командалар:\n/task — көн бурысы\n/stats — уңыштарым\n/top — рейтинг\n/settings — көйләүҙәр\n/cancel — ғәмәлде туҡтатырға\n\nСайт: {site}"],
"blocked": ["Аккаунт заблокирован.", "Аккаунт блокланған."],
"too_long": ["Перевод слишком длинный (до 400 символов).", "Тәржемә бик оҙон (400 символға тиклем)."],
}
PAIRS = {"ba-ru": ["башкирский → русский", "башҡортса → русса"], "ba-en": ["башкирский → английский", "башҡортса → инглизсә"],
         "ba-kk": ["башкирский → казахский", "башҡортса → ҡаҙаҡса"], "ba-alt": ["башкирский → алтайский", "башҡортса → алтайса"],
         "ba-ar": ["башкирский → арабский", "башҡортса → ғәрәпсә"], "ba-sah": ["башкирский → якутский", "башҡортса → саха телендә"],
         "ba-zh": ["башкирский → китайский", "башҡортса → ҡытайса"]}

def tx(tg, key, **kw):
    s = TX[key][1 if tg.lang == "ba" else 0]
    return s.format(**{k: (html.escape(str(v)) if isinstance(v, str) else v) for k, v in kw.items()}) if kw else s
def pn(tg, p): return PAIRS.get(p, [p, p])[1 if tg.lang == "ba" else 0]
def ib(*rows): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in r] for r in rows])
def menu(tg): return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text=tx(tg, "m_task"))], [KeyboardButton(text=tx(tg, "m_stats")), KeyboardButton(text=tx(tg, "m_top")), KeyboardButton(text=tx(tg, "m_set"))]])
def is_btn(text, key): return text in TX[key]

# ---------- работа с базой ----------
class Ctx:
    """Открывает сессию БД и запись пользователя Telegram; сохраняет состояние при выходе."""
    def __init__(self, tg_id): self.tg_id = tg_id
    def __enter__(self):
        self.s = SessionLocal()
        self.tg = self.s.get(TgUser, self.tg_id) or TgUser(tg_id=self.tg_id)
        self.s.add(self.tg)
        self.u = self.s.get(User, self.tg.user_id) if self.tg.user_id else None
        return self
    def __exit__(self, et, *a):
        if et is None: self.s.commit()
        else: self.s.rollback()
        self.s.close()
    @property
    def data(self): return json.loads(self.tg.data or "{}")
    def set(self, state, **data): self.tg.state, self.tg.data = state, json.dumps(data, ensure_ascii=False)
    def today(self): return extra.done_today(self.s, self.u) if self.u else 0

class AnswerData:  # тот же формат, что принимает сайт
    def __init__(self, fragment_id, pair, kind, text=""): self.fragment_id, self.pair, self.kind, self.text = fragment_id, pair, kind, text

# ---------- обработчики ----------
dp = Dispatcher()

async def show_menu(m: Message, c: Ctx, text):
    c.set("")
    await m.answer(text, reply_markup=menu(c.tg))

@dp.message(CommandStart())
async def start(m: Message, command: CommandObject):
    arg = (command.args or "").strip()
    with Ctx(m.from_user.id) as c:
        if m.from_user.language_code == "ba" and not c.tg.user_id: c.tg.lang = "ba"
        if arg.startswith("link_"):                      # привязка к аккаунту сайта
            u = links.use_code(c.s, "tg_link", arg[5:])
            if not u: return await m.answer(tx(c.tg, "link_bad"))
            for other in c.s.query(TgUser).filter(TgUser.user_id == u.id, TgUser.tg_id != c.tg_id): other.user_id = None
            c.tg.user_id, c.u = u.id, u
            return await show_menu(m, c, tx(c.tg, "linked", name=u.name))
        if c.u:
            if c.u.blocked: return await m.answer(tx(c.tg, "blocked"))
            return await show_menu(m, c, tx(c.tg, "welcome_back", name=c.u.name, streak=live_streak(c.u), today=c.today(), goal=GOAL))
        c.set("reg_name", class_code=arg if arg and not arg.startswith("link_") else "")
        await m.answer(tx(c.tg, "hello"))

@dp.message(Command("cancel"))
async def cancel(m: Message):
    with Ctx(m.from_user.id) as c:
        if not c.u: return await m.answer(tx(c.tg, "hello"))
        await show_menu(m, c, tx(c.tg, "cancel"))

@dp.message(Command("help"))
async def help_(m: Message):
    with Ctx(m.from_user.id) as c: await m.answer(tx(c.tg, "help", site=SITE), reply_markup=menu(c.tg) if c.u else None)

@dp.message(Command("task"))
async def cmd_task(m: Message): await send_task(m.chat.id, m.from_user.id, m.bot)

@dp.message(Command("stats"))
async def cmd_stats(m: Message): await stats(m)

@dp.message(Command("top"))
async def cmd_top(m: Message): await top(m)

@dp.message(Command("settings"))
async def cmd_settings(m: Message): await settings(m)

@dp.message(Command("lang"))
async def cmd_lang(m: Message):
    with Ctx(m.from_user.id) as c:
        c.tg.lang = "ru" if c.tg.lang == "ba" else "ba"
        await m.answer(tx(c.tg, "cancel"), reply_markup=menu(c.tg) if c.u else None)

MENU_KEYS = ("m_task", "m_stats", "m_top", "m_set")

@dp.message(F.text)
async def text(m: Message):
    t = m.text.strip()
    with Ctx(m.from_user.id) as c:
        st = c.tg.state
        if c.u and any(is_btn(t, k) for k in MENU_KEYS): st = ""   # кнопка меню прерывает ввод
        if st == "reg_name":                              # регистрация: имя
            name = " ".join(t.split())
            if not 1 <= len(name) <= 40 or name.startswith("/"): return await m.answer(tx(c.tg, "bad_name"))
            code = c.data.get("class_code", "")
            u = User(name=name, email=f"tg{c.tg_id}@telegram.invalid", password="!", role="student")
            c.s.add(u); c.s.flush(); c.tg.user_id, c.u = u.id, u
            inv = links.find_invite(c.s, code)
            if inv:
                links.apply_invite(c.s, u, inv)
                await m.answer(tx(c.tg, "class_ok", cls=u.class_name, school=u.school))
                return await show_menu(m, c, tx(c.tg, "ready"))
            c.set("reg_class")
            return await m.answer(tx(c.tg, "ask_class", name=name), reply_markup=ib([(tx(c.tg, "skip"), "skipclass")]))
        if not c.u: c.set("reg_name"); return await m.answer(tx(c.tg, "hello"))
        if c.u.blocked: return await m.answer(tx(c.tg, "blocked"))
        if st in ("reg_class", "class"):                  # код класса
            inv = links.find_invite(c.s, t)
            if not inv: return await m.answer(tx(c.tg, "bad_class"), reply_markup=ib([(tx(c.tg, "skip"), "skipclass")]))
            links.apply_invite(c.s, c.u, inv)
            await m.answer(tx(c.tg, "class_ok", cls=c.u.class_name, school=c.u.school))
            return await show_menu(m, c, tx(c.tg, "ready"))
        if st == "fix":                                   # исправленный перевод
            if len(t) > 400: return await m.answer(tx(c.tg, "too_long"))
            d = c.data
            return await answer(m.chat.id, m.bot, c, d["fid"], "correct", t)
    if is_btn(t, "m_task"): return await send_task(m.chat.id, m.from_user.id, m.bot)
    if is_btn(t, "m_stats"): return await stats(m)
    if is_btn(t, "m_top"): return await top(m)
    if is_btn(t, "m_set"): return await settings(m)
    with Ctx(m.from_user.id) as c: await m.answer(tx(c.tg, "help", site=SITE), reply_markup=menu(c.tg))

# ---------- задание дня ----------
async def send_task(chat_id, tg_id, bot, extra_mode=False):
    with Ctx(tg_id) as c:
        if not c.u: c.set("reg_name"); return await bot.send_message(chat_id, tx(c.tg, "hello"))
        d = c.data if c.tg.state in ("task", "fix") else {}
        if not d.get("items") or d.get("i", 0) >= len(d["items"]) or extra_mode:
            if c.u and c.u.pair and c.u.pair != c.tg.pair: c.tg.pair = c.u.pair
            daily = extra.make_daily(c.s, c.u, c.tg.pair, extra_mode)
            if not daily["items"]:
                c.set("")
                if extra_mode or daily["done_today"] < daily["goal"]: return await bot.send_message(chat_id, tx(c.tg, "no_more"), reply_markup=menu(c.tg))
                return await bot.send_message(chat_id, tx(c.tg, "done_title", today=daily["done_today"], goal=daily["goal"]), reply_markup=ib([(tx(c.tg, "b_more"), "more")]))
            d = {"items": [{"id": x["id"], "ba": x["text_ba"], "auto": x["auto"], "src": x["source"]["doc"], "pos": x["source"]["position"]} for x in daily["items"]],
                 "i": 0, "xp": 0, "fixes": 0, "extra": extra_mode}
        it = d["items"][d["i"]]
        head = f"✍️ {d['i'] + 1}/{len(d['items'])} · {pn(c.tg, c.tg.pair)}\n📜 {html.escape(it['src'])} · № {it['pos']}\n\n<b>{html.escape(it['ba'])}</b>\n\n"
        if it["auto"]:
            c.set("task", **d)
            say_row = [[(tx(c.tg, "b_say"), f"say:{it['id']}")]] if can_say(it["id"], it["ba"]) else []   # без озвучки кнопки нет
            kb = ib([(tx(c.tg, "b_ok"), f"ok:{it['id']}"), (tx(c.tg, "b_fix"), f"fix:{it['id']}")], *say_row)
            await bot.send_message(chat_id, head + tx(c.tg, "auto") + f"\n<i>{html.escape(it['auto'])}</i>", reply_markup=kb)
        else:
            d["fid"] = it["id"]; c.set("fix", **d)
            await bot.send_message(chat_id, head + tx(c.tg, "write_own"),
                                   reply_markup=ib([(tx(c.tg, "b_say"), f"say:{it['id']}")]) if can_say(it["id"], it["ba"]) else None)

async def answer(chat_id, bot, c: Ctx, fid, kind, text=""):
    d = c.data
    try:
        r = extra.submit_answer(c.s, c.u, AnswerData(fid, c.tg.pair, kind, text))
    except HTTPException as e:
        return await bot.send_message(chat_id, f"⚠️ {html.escape(str(e.detail))}")
    lines = [tx(c.tg, "xp", xp=r["xp"]) if r["xp"] else tx(c.tg, "accepted")]
    if r["error"]: lines = [tx(c.tg, "trap", right=r["right"] or "")]
    elif r["fixed"]: lines = [tx(c.tg, "fixed", xp=r["xp"]) if r["xp"] else tx(c.tg, "fixed0")]; d["fixes"] = d.get("fixes", 0) + 1
    if r["status"] == "confirmed": lines.append(tx(c.tg, "confirmed"))
    if r["status"] == "expert_review": lines.append(tx(c.tg, "expert"))
    if r["goal_reached_now"]:
        lines.append(tx(c.tg, "goal_now"))
        if r.get("flame_xp"): lines.append(tx(c.tg, "flame_xp", xp=r["flame_xp"]))
    d["xp"] = d.get("xp", 0) + r["xp"]; d["i"] = d.get("i", 0) + 1; d.pop("fid", None)
    if d["i"] >= len(d.get("items", [])):
        c.set("")
        lines.append("\n" + tx(c.tg, "finish", xp=d["xp"], fixes=d["fixes"]))
        return await bot.send_message(chat_id, "\n".join(lines), reply_markup=ib([(tx(c.tg, "b_more"), "more")]))
    c.set("task", **d)
    await bot.send_message(chat_id, "\n".join(lines), reply_markup=ib([(tx(c.tg, "b_next"), "next")]))

@dp.callback_query()
async def on_button(q: CallbackQuery):
    data, chat, bot = q.data or "", q.message.chat.id, q.bot
    await q.answer()
    if data in ("next", "more"):
        try: await q.message.edit_reply_markup(reply_markup=None)
        except Exception: pass
        return await send_task(chat, q.from_user.id, bot, extra_mode=data == "more")
    if data.startswith("pair:"):
        with Ctx(q.from_user.id) as c:
            p = data[5:]
            if p in PAIRS:
                c.tg.pair = p; c.set("")
                if c.u: c.u.pair = p          # пара хранится в профиле: сайт и бот показывают одно и то же
            return await q.message.edit_text(tx(c.tg, "pair_ok", pair=pn(c.tg, c.tg.pair)))
    if data.startswith("say:"):
        return await say(q, int(data[4:]))
    with Ctx(q.from_user.id) as c:
        if not c.u: return
        if data == "skipclass":
            try: await q.message.edit_reply_markup(reply_markup=None)
            except Exception: pass
            return await show_menu(q.message, c, tx(c.tg, "ready"))
        if data.startswith(("ok:", "fix:")):
            kind, fid = data.split(":"); fid = int(fid)
            d = c.data
            items = d.get("items", [])
            if c.tg.state not in ("task", "fix") or d.get("i", 0) >= len(items) or items[d["i"]]["id"] != fid: return
            try: await q.message.edit_reply_markup(reply_markup=None)
            except Exception: pass
            if kind == "ok": return await answer(chat, bot, c, fid, "confirm")
            d["fid"] = fid; c.set("fix", **d)
            return await bot.send_message(chat, tx(c.tg, "send_fix", auto=items[d["i"]]["auto"]))
        if data == "s:pair":
            return await bot.send_message(chat, tx(c.tg, "pick_pair"), reply_markup=ib(*[[(pn(c.tg, p), f"pair:{p}")] for p in PAIRS]))
        if data == "s:lang":
            c.tg.lang = "ru" if c.tg.lang == "ba" else "ba"
            return await show_menu(q.message, c, tx(c.tg, "cancel"))
        if data == "s:rem":
            c.tg.remind = not c.tg.remind
            return await q.message.edit_text(settings_text(c), reply_markup=settings_kb(c))
        if data == "s:class":
            c.set("class"); return await bot.send_message(chat, tx(c.tg, "send_class"))
        if data == "s:site":
            code = links.make_code(c.s, "site_login", c.u.id, 10)
            return await bot.send_message(chat, tx(c.tg, "site_link", url=f"{SITE}/#/tg/{code}"), disable_web_page_preview=True)

def can_say(fid, text=""):
    """Озвучить фрагмент можно, если есть синтез, готовый файл озвучки или утверждённая запись голоса."""
    return tts.available() or bool(text and tts.ready(text)) or (extra.AUDIO / f"{fid}.webm").exists()

async def say(q: CallbackQuery, fid):
    with Ctx(q.from_user.id) as c:
        f = c.s.get(Fragment, fid)
        if not f: return
        text, msg = f.text_ba, tx(c.tg, "no_voice")
    rec = extra.AUDIO / f"{fid}.webm"
    if rec.exists():                                   # утверждённая запись носителя важнее синтеза
        return await q.message.answer_audio(FSInputFile(rec, filename="tamga.webm"), title=text[:60], performer="Тамға")
    path = await asyncio.to_thread(tts.synth, text)        # вернёт готовый файл и без модели
    if not path: return await q.message.answer(msg)
    await q.message.answer_audio(FSInputFile(path, filename="tamga.wav"), title=text[:60], performer="Тамға")

# ---------- прогресс, рейтинг, настройки ----------
async def stats(m: Message):
    with Ctx(m.from_user.id) as c:
        if not c.u: c.set("reg_name"); return await m.answer(tx(c.tg, "hello"))
        A = c.s.query(Answer).filter_by(user_id=c.u.id).all()
        words = set()
        for (t,) in c.s.query(Fragment.text_ba).filter(Fragment.id.in_({a.fragment_id for a in A} or [0])): words |= set(extra.nrm(t).split())
        n, errs = len(A), sum(a.error for a in A)
        school = f"\n🏫 {c.u.school} {c.u.class_name}" if c.u.school else ""
        await m.answer(tx(c.tg, "stats", name=c.u.name, level=c.u.xp // 500 + 1, xp=c.u.xp, streak=live_streak(c.u), today=c.today(), goal=GOAL,
                          vocab=len(words), fixes=sum(a.fixed for a in A), acc=round(100 * (n - errs) / n) if n else 0, school=school), reply_markup=menu(c.tg))

async def top(m: Message):
    with Ctx(m.from_user.id) as c:
        if not c.u: c.set("reg_name"); return await m.answer(tx(c.tg, "hello"))
        since = dt.date.today() - dt.timedelta(days=6)
        pts = {}
        for a in c.s.query(Answer).filter(Answer.day >= since): pts[a.user_id] = pts.get(a.user_id, 0) + a.xp
        users = {u.id: u for u in c.s.query(User).filter(User.id.in_(pts or [0]), User.role == "student", User.blocked == False)}  # noqa: E712
        rows = sorted(((uid, p) for uid, p in pts.items() if uid in users), key=lambda r: -r[1])
        if not rows: return await m.answer(tx(c.tg, "top_empty"))
        medal = ["🥇", "🥈", "🥉"]
        lines = [tx(c.tg, "top")]
        for i, (uid, p) in enumerate(rows[:10]):
            mark = " ← " if uid == c.u.id else ""
            lines.append(f"{medal[i] if i < 3 else f'{i + 1}.'} {html.escape(users[uid].name)} {html.escape(users[uid].class_name)} — {p}{mark}")
        me = next((i for i, r in enumerate(rows) if r[0] == c.u.id), None)
        if me is not None and me >= 10: lines.append(f"…\n{me + 1}. {html.escape(c.u.name)} — {rows[me][1]}")
        await m.answer("\n".join(lines))

def settings_text(c): return tx(c.tg, "settings", pair=pn(c.tg, c.tg.pair), remind=tx(c.tg, "on" if c.tg.remind else "off"))
def settings_kb(c):
    return ib([(tx(c.tg, "s_pair"), "s:pair")], [(tx(c.tg, "s_rem"), "s:rem")], [(tx(c.tg, "s_class"), "s:class")],
              [(tx(c.tg, "s_site"), "s:site")], [(tx(c.tg, "s_lang"), "s:lang")])

async def settings(m: Message):
    with Ctx(m.from_user.id) as c:
        if not c.u: c.set("reg_name"); return await m.answer(tx(c.tg, "hello"))
        await m.answer(settings_text(c), reply_markup=settings_kb(c))

# ---------- напоминания в течение дня ----------
# Пока дневная норма не выполнена, куница напоминает о ней. Текст зависит от того, сколько часов
# осталось до нового дня (чем ближе полночь — тем настойчивее), а язык — от языка пользователя в боте
# (русский или башкирский). День делится на шесть «ступеней» по 4 часа; из каждой ступени отправляется
# не больше одного напоминания в день, фраза выбирается случайно из трёх.
# REMIND_FROM (по умолчанию 8) — до этого часа бот молчит, чтобы не будить ночью; REMIND_FROM=0 — слать всегда.
REMIND_TIERS = [
 # осталось 24–20 часов (00:00–03:59)
 [["Не забудь про ежедневные задания!", "Регулярно проходи задания.", "Позанимаемся башкирским?"],
  ["Көндәлек биремдәрҙе онотма!", "Биремдәрҙе даими үтә.", "Башҡортса шөғөлләнәйекме?"]],
 # осталось 20–16 часов (04:00–07:59)
 [["Пройди задания — это не сложно!", "Я требую всего пару минут в день!", "Пойдём заниматься?"],
  ["Биремдәрҙе үтеп сыҡ — был ҡыйын түгел!", "Миңә көнөнә бер нисә минут ҡына кәрәк!", "Әйҙә шөғөлләнәйек?"]],
 # осталось 16–12 часов (08:00–11:59)
 [["Самое время для башкирского!", "У тебя есть невыполненное задание.", "Пройдёшь задания — разрешу погладить!"],
  ["Башҡорт теле өсөн иң ҡулай ваҡыт!", "Һинең үтәлмәгән биремең бар.", "Биремдәрҙе үтһәң — һыйпарға рөхсәт итәм!"]],
 # осталось 12–8 часов (12:00–15:59)
 [["Ты что, забыл обо мне?", "А как же башкирский?", "Ты скоро потеряешь стрик..."],
  ["Һин мине оноттоңмо әллә?", "Ә башҡорт теле нисек инде?", "Һин оҙаҡламай утыңды юғалтаһың..."]],
 # осталось 8–4 часа (16:00–19:59)
 [["Задания сами себя не пройдут.", "{name}, я больше тебе не нужна..?", "Пройди задания."],
  ["Биремдәр үҙҙәрен үҙҙәре үтмәй.", "{name}, мин һиңә бүтән кәрәк түгелме..?", "Биремдәрҙе үт."]],
 # осталось 4–0 часов (20:00–23:59)
 [["......огонёк?", "ЭЙ. Ты обижаешь меня.", "Я начну кусаться."],
  ["......утҡайым?", "ЭЙ. Һин мине рәнйетәһең.", "Мин тешләй башлайым."]],
]

async def reminders(bot: Bot):
    while True:
        try:
            now_local = dt.datetime.now(TZ)
            if now_local.hour >= REMIND_FROM:
                tier = now_local.hour // 4                      # 0..5: какая четырёхчасовая ступень дня идёт
                today = dt.date.today()
                s = SessionLocal()
                try:
                    for tg in s.query(TgUser).filter(TgUser.remind == True, TgUser.user_id.isnot(None)).all():  # noqa: E712
                        if tg.last_remind == today and (tg.remind_tier if tg.remind_tier is not None else -1) >= tier:
                            continue                            # из этой ступени сегодня уже напоминали
                        n = s.query(Answer).filter_by(user_id=tg.user_id, day=today, error=False).count()
                        tg.last_remind, tg.remind_tier = today, tier
                        s.commit()
                        if n < GOAL:
                            u = s.get(User, tg.user_id)
                            if not u or u.blocked: continue
                            phrase = random.choice(REMIND_TIERS[tier][1 if tg.lang == "ba" else 0])
                            try: await bot.send_message(tg.tg_id, phrase.format(name=html.escape(u.name)), reply_markup=menu(tg))
                            except Exception as e: log.info("напоминание не доставлено %s: %s", tg.tg_id, e)
                            await asyncio.sleep(0.05)   # лимиты Telegram
                finally:
                    s.close()
        except Exception:
            log.exception("ошибка в напоминаниях")
        await asyncio.sleep(600)

async def main():
    if not TOKEN: sys.exit("Не задан TELEGRAM_TOKEN: получите токен у @BotFather и впишите его в файл .env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Base.metadata.create_all(engine); ensure_columns(); seed()
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await bot.set_my_commands([BotCommand(command="task", description="Задание дня / Көн бурысы"), BotCommand(command="stats", description="Мой прогресс / Уңыштарым"),
                               BotCommand(command="top", description="Рейтинг"), BotCommand(command="settings", description="Настройки / Көйләүҙәр"),
                               BotCommand(command="lang", description="Русский ⇄ Башҡортса"), BotCommand(command="cancel", description="Отменить / Туҡтатырға"),
                               BotCommand(command="help", description="Помощь / Ярҙам")])
    asyncio.create_task(reminders(bot))
    log.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
