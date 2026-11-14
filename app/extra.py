"""Регистрация, школы, ежедневные задания, согласование переводов, база, рейтинги, API для внешних систем."""
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import os, re, io, csv, time, threading, random, smtplib, secrets, hashlib, datetime as dt
from email.message import EmailMessage
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import *
from security import *
import asr
from quality import not_bashkir
import logging; log = logging.getLogger("tamga")
from api import EMAIL, clean, user_dict, touch_streak, STAFF, norm, live_streak
import re, random, csv, io
from fastapi.responses import Response, FileResponse

router = APIRouter(prefix="/api")
_h = lambda c: hashlib.sha256(c.encode()).hexdigest()

def send_mail(to, code):
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"[Тамға] код подтверждения для {to}: {code}")
        return False
    m = EmailMessage(); m["Subject"] = "Код подтверждения — Тамға"; m["To"] = to
    m["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
    m.set_content(f"Ваш код: {code}\nОн действует 15 минут.")
    port = int(os.getenv("SMTP_PORT", "587"))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as c: c.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")); c.send_message(m)
        else:
            with smtplib.SMTP(host, port, timeout=20) as c: c.starttls(); c.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")); c.send_message(m)
    except Exception as e:
        print(f"[Тамға] ОШИБКА отправки почты: {e!r}")
        raise HTTPException(502, "Не удалось отправить письмо. Проверьте адрес почты или попробуйте позже")
    return True

class StartIn(BaseModel):
    name: str = Field(min_length=1, max_length=80); email: str = Field(max_length=160, pattern=EMAIL)
    password: str = Field(min_length=8, max_length=128)
    class_code: str = Field(default="", max_length=12)   # школа и класс берутся только из кода класса от учителя
class ResendIn(BaseModel): email: str = Field(max_length=160)
class ConfirmIn(BaseModel): email: str = Field(max_length=160); code: str = Field(max_length=6)
class CommentIn(BaseModel): text: str
class AnswerIn(BaseModel): fragment_id: int; pair: str; kind: str; text: str = Field(default="", max_length=400)
class SchoolSet(BaseModel): school_id: int | None = None; grade: int | None = Field(default=None, ge=1, le=11); letter: str = Field(default="", max_length=2)
class PairSet(BaseModel): pair: str = Field(max_length=10)
class DecideIn(BaseModel): pair: str; translation: str = Field(max_length=400)
class SliceIn(BaseModel): text: str = Field(max_length=200000); source_doc: str = Field(max_length=200); chapter: str = Field(default="", max_length=120); mode: str = "sentence"; pair: str = "ba-ru"
class FragIn(BaseModel):
    text_ba: str = Field(max_length=600); source_doc: str = Field(default="", max_length=200); chapter: str = Field(default="", max_length=120); position: int = 0
    audio_from: int | None = None; audio_to: int | None = None; auto: dict[str, dict[str, str]] = {}
class SchoolIn(BaseModel): city: str = Field(max_length=80); name: str = Field(max_length=160)

@router.post("/register/start")
def reg_start(d: StartIn, request: Request, s: Session = Depends(db)):
    # С одного адреса часто регистрируется целый класс или зал (общий Wi-Fi), поэтому лимит щедрый;
    # от перебора защищает лимит на сам адрес почты ниже.
    limiter.hit("regs:" + ip_of(request), int(os.getenv("REG_PER_IP", "80")), 600)
    email = d.email.lower()
    if s.query(User).filter_by(email=email).first(): raise HTTPException(409, "Этот email уже зарегистрирован")
    # Школа и класс не выбираются из списка: ученик попадает в них только по коду класса,
    # который выдаёт учитель (огромный список районов и школ из регистрации убран).
    from links import find_invite
    inv = find_invite(s, d.class_code)
    if d.class_code.strip() and not inv: raise HTTPException(400, "Код класса не найден — проверьте его у учителя")
    school_id, grade, letter = (inv.school_id, inv.grade, inv.letter) if inv else (None, None, "")
    code = f"{secrets.randbelow(10**6):06d}"
    s.merge(EmailCode(email=email, code_hash=_h(code), name=clean(d.name, "Имя", 80), pw=hash_pw(d.password),
                      school_id=school_id, grade=grade, letter=letter,
                      attempts=0, expires_at=now() + dt.timedelta(minutes=15)))
    s.commit()
    sent = send_mail(email, code)
    out = {"ok": True}
    if not sent and os.getenv("DEV_SHOW_CODE", "1") == "1": out["dev_code"] = code  # только для разработки: DEV_SHOW_CODE=0 на сервере
    return out

@router.post("/register/resend")
def reg_resend(d: ResendIn, request: Request, s: Session = Depends(db)):
    email = d.email.lower(); limiter.hit("regr:" + email, 5, 600)
    e = s.get(EmailCode, email)
    if not e: raise HTTPException(400, "Сначала заполните регистрацию")
    if e.expires_at > now() + dt.timedelta(minutes=14): raise HTTPException(429, "Подождите минуту перед повторной отправкой")
    code = f"{secrets.randbelow(10**6):06d}"
    e.code_hash, e.attempts, e.expires_at = _h(code), 0, now() + dt.timedelta(minutes=15); s.commit()
    sent = send_mail(email, code)
    return {"ok": True, **({"dev_code": code} if not sent and os.getenv("DEV_SHOW_CODE", "1") == "1" else {})}

@router.post("/register/confirm")
def reg_confirm(d: ConfirmIn, s: Session = Depends(db)):
    email = d.email.lower(); limiter.hit("regc:" + email, 10, 600)
    e = s.get(EmailCode, email)
    if not e or e.expires_at < now(): raise HTTPException(400, "Код истёк — запросите новый")
    e.attempts += 1
    if e.attempts > 5: s.delete(e); s.commit(); raise HTTPException(400, "Слишком много попыток — запросите новый код")
    if not secrets.compare_digest(e.code_hash, _h(d.code.strip())): s.commit(); raise HTTPException(400, "Неверный код")
    sc = s.get(School, e.school_id) if e.school_id else None
    u = User(name=e.name, email=e.email, password=e.pw, role="student", school=sc.name if sc else "",
             class_name=f"{e.grade}{e.letter}" if sc and e.grade else "", school_id=e.school_id, grade=e.grade, letter=e.letter)
    s.add(u); s.delete(e); s.commit(); s.refresh(u)
    audit(s, u.id, "register"); s.commit()
    return {"token": new_token(s, u), "user": user_dict(u)}

PAIRS = {"ba-ru": "башкирский → русский", "ba-en": "башкирский → английский", "ba-kk": "башкирский → казахский", "ba-alt": "башкирский → алтайский", "ba-ar": "башкирский → арабский", "ba-sah": "башкирский → якутский", "ba-zh": "башкирский → китайский"}
DAILY = 5          # столько верных заданий держат огонёк
EXTRA_BATCH = 10   # размер порции в режиме «продолжить переводить»
PLANT_RATE = float(os.getenv("PLANT_RATE", "0.3"))   # как часто подмешивается заведомо неверный вариант
def nrm(t): return " ".join(re.sub(r"[.,!?;:«»\"“”—-]", " ", t.lower().replace("ё", "е")).split())
def pair_ok(p):
    if p not in PAIRS: raise HTTPException(400, "Неизвестная языковая пара")
    return p

# ---- школы: город → школа → класс и буква ----
@router.get("/schools/cities")
def cities(s: Session = Depends(db)): return [c for (c,) in s.query(School.city).distinct().order_by(School.city)]

@router.get("/schools")
def schools(city: str, s: Session = Depends(db)):
    return [{"id": x.id, "name": x.name} for x in s.query(School).filter_by(city=city).order_by(School.name)]

@router.post("/admin/schools")
def add_schools(items: list[SchoolIn], u: User = Depends(require("admin")), s: Session = Depends(db)):
    n = 0
    for i in items[:5000]:
        c, nm = clean(i.city, "Город", 80), clean(i.name, "Школа", 160)
        if not s.query(School).filter_by(city=c, name=nm).first(): s.add(School(city=c, name=nm)); n += 1
    audit(s, u.id, "schools_added", str(n)); s.commit()
    return {"added": n}

@router.patch("/me/school")
def set_school(d: SchoolSet, u: User = Depends(require("teacher", "admin")), s: Session = Depends(db)):
    """Школу и класс из списка выбирает только учитель (чтобы выдать код класса) или администратор.
    Ученик попадает в школу и класс по коду класса — список из сотен школ ему не показывается."""
    sc = s.get(School, d.school_id) if d.school_id else None
    if d.school_id and not sc: raise HTTPException(400, "Школа не найдена")
    u.school_id, u.school = (sc.id, sc.name) if sc else (None, "")
    u.grade, u.letter = (d.grade, d.letter.strip().upper()) if sc and d.grade else (None, "")
    u.class_name = f"{u.grade}{u.letter}" if u.grade else ""
    s.commit()
    return user_dict(u)

@router.patch("/me/pair")
def set_pair(d: PairSet, u: User = Depends(current_user), s: Session = Depends(db)):
    """Языковая пара, с которой работает пользователь: хранится в профиле, а не в браузере."""
    u.pair = pair_ok(d.pair); s.commit()
    return user_dict(u)

# ---- ежедневное задание ----
def done_today(s, u, day=None):
    """Сколько заданий зачтено сегодня: верные ответы, без тех, где поверили подставной ошибке."""
    return s.query(Answer).filter_by(user_id=u.id, day=day or dt.date.today(), error=False).count()

_MD = {"t": 0.0, "v": set()}
def media_docs(s):
    """Источники, у которых загружен аудиофайл (список обновляется раз в полминуты)."""
    if time.time() - _MD["t"] > 30: _MD.update(t=time.time(), v={d for (d,) in s.query(Media.doc)})
    return _MD["v"]

def frag_dict(f, docs=(), **kw):
    return {"id": f.id, "text_ba": f.text_ba,
            "source": {"doc": f.source_doc, "chapter": f.chapter, "position": f.position, "audio_from": f.audio_from, "audio_to": f.audio_to},
            "media": f.audio_from is not None and f.source_doc in docs, **kw}

@router.get("/daily")
def daily(pair: str = "ba-ru", extra: bool = False, u: User = Depends(current_user), s: Session = Depends(db)):
    return make_daily(s, u, pair, extra)

def make_daily(s, u, pair="ba-ru", extra=False):
    """Выдаёт задание дня (общая логика для сайта и Telegram-бота)."""
    pair_ok(pair)
    done = [i for (i,) in s.query(Answer.fragment_id).filter_by(user_id=u.id, pair=pair)]
    today = done_today(s, u)
    left = EXTRA_BATCH if extra else max(0, DAILY - today)   # extra — переводить сверх нормы, порциями
    conf = {i for (i,) in s.query(Consensus.fragment_id).filter_by(pair=pair, status="confirmed")}
    cnt = dict(s.query(Answer.fragment_id, func.count()).filter_by(pair=pair).group_by(Answer.fragment_id).all())
    md = media_docs(s)
    cand = [f for f in s.query(Fragment).filter_by(active=True).all() if f.id not in done]
    cand.sort(key=lambda f: (f.id in conf, cnt.get(f.id, 0), random.random()))
    out = []
    for f in cand[:left]:
        a = s.query(AutoTr).filter_by(fragment_id=f.id, pair=pair).first()
        planted = bool(a and a.wrong and random.random() < PLANT_RATE)
        shown = (a.wrong if planted else a.text) if a else ""
        s.query(Shown).filter_by(user_id=u.id, fragment_id=f.id, pair=pair).delete()
        s.add(Shown(user_id=u.id, fragment_id=f.id, pair=pair, shown_text=shown, planted=planted))
        out.append(frag_dict(f, md, auto=shown, mode="check" if shown else "write"))
    s.commit()
    for it in out:                                               # запись голоса, ожидающая оценки учеников
        for r in s.query(VoiceRec).filter_by(fragment_id=it["id"], status="voting").filter(VoiceRec.user_id != u.id):
            if not s.query(VoiceVote).filter_by(rec_id=r.id, user_id=u.id).first():
                it["rec"] = {"id": r.id, "token": r.token}; break
    return {"items": out, "done_today": today, "goal": DAILY, "extra": extra, "left_total": max(0, len(cand) - len(out))}

# Согласование: решают доли, а не число людей.
#   варианты, которые дали меньше NOISE (20%) ответивших, не засчитываются — это шум/ошибки;
#   среди оставшихся лидер с долей >= SHARE (60%) подтверждается;
#   если сильных вариантов несколько и ни один не набрал SHARE — случай уходит экспертам.
#   MIN_VOTERS — минимум ответов, чтобы вообще считать проценты (один человек — это ещё не 100%).
MIN_VOTERS = int(os.getenv("CONSENSUS_MIN_VOTERS", os.getenv("CONSENSUS_MIN", "3")))
NOISE = float(os.getenv("CONSENSUS_NOISE", "0.2"))
SHARE = float(os.getenv("CONSENSUS_SHARE", "0.6"))

# Синонимичность: варианты, которые значат одно и то же, считаются вместе.
#   1) регистр, «ё» и пунктуация не важны (nrm);
#   2) порядок слов не важен — «Я сегодня читаю книгу» и «Сегодня я читаю книгу» это один вариант;
#   3) слова из словаря синонимов (synonyms.txt) сводятся к одному;
#   4) если варианты отличаются ровно одним словом и это слово похоже (книгу / книжку) — тоже один вариант,
#      а «вчера» и «сегодня» непохожи, поэтому подставная ошибка с верным переводом не сольётся.
SYN_FILE = Path(__file__).parent / "synonyms.txt"

def load_syn():
    m = {}
    if SYN_FILE.exists():
        for line in SYN_FILE.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if "=" not in line: continue
            head, rest = line.split("=", 1)
            c = nrm(head)
            if not c: continue
            m[c] = c
            for w in rest.split(","):
                w = nrm(w)
                if w: m[w] = c
    return m

SYN = load_syn()
SIM = float(os.getenv("CONSENSUS_WORD_SIM", "0.7"))   # насколько похожи слова, чтобы считаться формой одного

def canon(t): return Counter(SYN.get(w, w) for w in nrm(t).split())

def same_meaning(a: Counter, b: Counter):
    if a == b: return True
    da, db = list((a - b).elements()), list((b - a).elements())
    return len(da) == 1 and len(db) == 1 and SequenceMatcher(None, da[0], db[0]).ratio() >= SIM

def tally(s, fid, pair):
    exact = {}
    for (t,) in s.query(Answer.text).filter(Answer.fragment_id == fid, Answer.pair == pair, Answer.text != ""):
        g = exact.setdefault(nrm(t), [t, 0]); g[1] += 1
    groups = []                                        # [представитель, сколько голосов, каноническая форма]
    for text, n in sorted(exact.values(), key=lambda g: -g[1]):
        k = canon(text)
        for g in groups:
            if same_meaning(g[2], k): g[1] += n; break
        else: groups.append([text, n, k])
    total = sum(g[1] for g in groups)
    return sorted([[g[0], g[1]] for g in groups], key=lambda g: -g[1]), total

XP_CONFIRMED = int(os.getenv("XP_CONFIRMED", "10"))   # начисляется, когда твой вариант попал в базу
XP_CATCH = int(os.getenv("XP_CATCH", "5"))            # за найденную подставную ошибку, сразу
XP_FLAME = int(os.getenv("XP_FLAME", "15"))           # бонус за зажжённый огонёк: выполнил дневную норму — получил больше XP
STREAK_REPAIR_XP = int(os.getenv("STREAK_REPAIR_XP", "100"))   # цена восстановления серии после одного пропущенного дня

def pay_confirmed(s, fid, pair, final):
    """Очки за перевод начисляются не за отправку, а когда вариант подтверждён другими
    и попал в базу. Иначе можно было бы набивать уровни любым набором букв."""
    if not final: return
    key = canon(final)
    for a in s.query(Answer).filter_by(fragment_id=fid, pair=pair).filter(Answer.xp == 0, Answer.error == False):  # noqa: E712
        if a.text and same_meaning(canon(a.text), key):
            u = s.get(User, a.user_id)
            if u: u.xp += XP_CONFIRMED; a.xp = XP_CONFIRMED

def recompute(s, fid, pair):
    c = s.query(Consensus).filter_by(fragment_id=fid, pair=pair).first() or Consensus(fragment_id=fid, pair=pair)
    s.add(c)
    if c.expert: return c
    variants, total = tally(s, fid, pair)
    if not total: c.status = "collecting"; return c
    strong = [g for g in variants if g[1] / total >= NOISE]
    best = variants[0]
    c.translation, c.confirmed = best[0], best[1]
    kept = sum(g[1] for g in strong) or 1
    if total < MIN_VOTERS: c.status = "collecting"
    elif best[1] / kept >= SHARE:
        c.status = "confirmed"; pay_confirmed(s, fid, pair, c.translation)
    elif len(strong) >= 2 and total >= max(5, MIN_VOTERS): c.status = "expert_review"
    else: c.status = "collecting"
    return c

@router.post("/answer")
def answer(d: AnswerIn, u: User = Depends(current_user), s: Session = Depends(db)):
    return submit_answer(s, u, d)

def submit_answer(s, u, d):
    """Принимает ответ на фрагмент (общая логика для сайта и Telegram-бота)."""
    limiter.hit(f"ans:{u.id}", 30, 60); pair_ok(d.pair)
    if d.kind not in ("confirm", "correct"): raise HTTPException(400, "Неизвестное действие")
    sh = s.query(Shown).filter_by(user_id=u.id, fragment_id=d.fragment_id, pair=d.pair).first()
    if not sh: raise HTTPException(400, "Это задание вам не выдавалось")
    if s.query(Answer).filter_by(user_id=u.id, fragment_id=d.fragment_id, pair=d.pair).first(): raise HTTPException(409, "Вы уже ответили")
    text, vote, err, fixed, xp = "", "", False, False, 0      # очки — только после подтверждения другими
    auto = s.query(AutoTr).filter_by(fragment_id=d.fragment_id, pair=d.pair).first()
    if d.kind == "confirm":
        if not sh.shown_text: raise HTTPException(400, "Здесь нужно ввести свой перевод")
        if sh.planted: err = True
        else: vote = sh.shown_text
    else:
        text = clean(d.text, "Перевод", 400)
        if sh.shown_text and nrm(text) == nrm(sh.shown_text):
            if sh.planted: err = True
            else: vote = text
        else:
            vote = text
            if sh.planted:
                fixed = True                                  # подставную ошибку не подтвердили — это засчитывается
                if auto and same_meaning(canon(text), canon(auto.text)): xp = XP_CATCH
    s.add(Answer(user_id=u.id, fragment_id=d.fragment_id, pair=d.pair, kind=d.kind, text=vote, planted=sh.planted, error=err, fixed=fixed, xp=xp, day=dt.date.today()))
    s.flush()
    c = recompute(s, d.fragment_id, d.pair)
    today_n = done_today(s, u)
    u.xp += xp
    if today_n >= DAILY: touch_streak(u)   # огонёк держат 5 верных заданий в день
    goal_now = today_n == DAILY and not err
    flame_xp = 0
    if goal_now:                           # огонёк зажёгся — бонусные XP (ровно раз в день: норма достигается один раз)
        flame_xp = XP_FLAME; u.xp += flame_xp
        audit(s, u.id, "flame_xp", str(flame_xp))
    s.delete(sh); s.commit()
    right = None
    if err or fixed: right = auto.text if auto else None
    return {"error": err, "fixed": fixed, "xp": xp, "planted": sh.planted, "right": right, "status": c.status, "user": user_dict(u),
            "today": today_n, "goal": DAILY, "goal_reached_now": goal_now, "flame_xp": flame_xp}

@router.get("/me/stats")
def my_stats(u: User = Depends(current_user), s: Session = Depends(db)):
    A = s.query(Answer).filter_by(user_id=u.id).order_by(Answer.id.desc()).all()
    n, fixes, errs = len(A), sum(a.fixed for a in A), sum(a.error for a in A)
    fr = {f.id: f for f in s.query(Fragment).filter(Fragment.id.in_({a.fragment_id for a in A[:6]} or [0]))}
    words = {w for a in A for w in nrm(fr[a.fragment_id].text_ba if a.fragment_id in fr else "").split()}
    allw = set()
    for (t,) in s.query(Fragment.text_ba).filter(Fragment.id.in_({a.fragment_id for a in A} or [0])): allw |= set(nrm(t).split())
    today = done_today(s, u)
    per_day = {}
    for a in A:
        if not a.error: per_day[a.day] = per_day.get(a.day, 0) + 1   # в норму идут только верные
    d0 = dt.date.today()
    days = [{"d": str(d0 - dt.timedelta(days=i)), "n": per_day.get(d0 - dt.timedelta(days=i), 0), "goal": per_day.get(d0 - dt.timedelta(days=i), 0) >= DAILY} for i in range(27, -1, -1)]
    full = sorted(d for d, k in per_day.items() if k >= DAILY)     # дни, когда норма выполнена
    best = run = 0
    for i, d in enumerate(full):
        run = run + 1 if i and d - full[i - 1] == dt.timedelta(days=1) else 1
        best = max(best, run)
    learn_xp = sum(int(x.detail or 0) for x in s.query(Audit).filter_by(user_id=u.id, action="learn_xp"))
    flame_xp = sum(int(x.detail or 0) for x in s.query(Audit).filter_by(user_id=u.id, action="flame_xp"))
    # огонёк погас, но пропущен ровно один день (вчера) — серию ещё можно выкупить за XP, как в Duolingo
    can_fix = u.last_active == d0 - dt.timedelta(days=2) and u.streak > 0
    return {"answers": n, "today": today, "days": days, "best_streak": max(best, live_streak(u)), "days_done": len(full),
            "can_fix": can_fix, "fix_cost": STREAK_REPAIR_XP, "lost_streak": u.streak if can_fix else 0,
            "xp_translate": sum(a.xp for a in A), "xp_learn": learn_xp, "xp_flame": flame_xp, "confirms": sum(1 for a in A if a.kind == "confirm"),
            "corrections": sum(1 for a in A if a.kind == "correct"), "since": str(u.created_at.date()), "goal": DAILY, "fixes": fixes, "errors": errs, "vocab": len(allw),
            "accuracy": round(100 * (n - errs) / n) if n else 0, "streak": live_streak(u), "user": user_dict(u),
            "recent": [{"text": fr[a.fragment_id].text_ba, "fixed": a.fixed, "error": a.error, "xp": a.xp, "at": a.created_at.isoformat()} for a in A[:6] if a.fragment_id in fr],
            "badges": {"first": n >= 1, "ten": n >= 10, "fifty": n >= 50, "fix": fixes >= 3, "streak": live_streak(u) >= 7, "vocab": len(allw) >= 50}}

# ---- восстановление серии за XP (как в Duolingo) ----
@router.post("/me/streak-fix")
def streak_fix(u: User = Depends(current_user), s: Session = Depends(db)):
    """Пропущен ровно один день — серию можно выкупить, потратив XP. Опыт здесь — валюта:
    рейтинги считаются по заработанным очкам из ответов, поэтому траты XP их не искажают."""
    d0 = dt.date.today()
    if not (u.last_active == d0 - dt.timedelta(days=2) and u.streak > 0):
        raise HTTPException(400, "Восстановить серию можно, только если пропущен ровно один день")
    if u.xp < STREAK_REPAIR_XP:
        raise HTTPException(400, f"Не хватает опыта: нужно {STREAK_REPAIR_XP} XP")
    u.xp -= STREAK_REPAIR_XP
    u.last_active = d0 - dt.timedelta(days=1)   # как будто вчерашняя норма выполнена: огонёк снова горит
    audit(s, u.id, "streak_fix", str(STREAK_REPAIR_XP)); s.commit()
    return {"user": user_dict(u), "cost": STREAK_REPAIR_XP, "streak": live_streak(u)}

# ---- база подтверждённых переводов ----
@router.get("/base")
def base(pair: str = "ba-ru", q: str = Query("", max_length=100), status: str = "confirmed", u: User = Depends(current_user), s: Session = Depends(db)):
    pair_ok(pair)
    cm = dict(s.query(FComment.fragment_id, func.count()).group_by(FComment.fragment_id).all())
    def variants(fid):
        g = {}
        for (t,) in s.query(Answer.text).filter(Answer.fragment_id == fid, Answer.pair == pair, Answer.text != ""):
            x = g.setdefault(nrm(t), [t, 0]); x[1] += 1
        n = sum(v[1] for v in g.values()) or 1
        return sorted(([v[0], v[1], round(100 * v[1] / n)] for v in g.values()), key=lambda v: -v[1])
    if status == "mine":
        rows = s.query(Answer, Fragment).join(Fragment, Fragment.id == Answer.fragment_id).filter(Answer.user_id == u.id, Answer.pair == pair, Answer.text != "").order_by(Answer.id.desc()).limit(200).all()
        cons = {c.fragment_id: c for c in s.query(Consensus).filter_by(pair=pair)}
        return [{**frag_dict(f, media_docs(s)), "translation": a.text, "mine": True, "status": cons[f.id].status if f.id in cons else "collecting", "final": cons[f.id].translation if f.id in cons else "",
                 "confirmed": cons[f.id].confirmed if f.id in cons else 0, "expert": False, "comments": cm.get(f.id, 0), "variants": []}
                for a, f in rows if not q or nrm(q) in nrm(f.text_ba + " " + a.text)]
    rows = s.query(Consensus, Fragment).join(Fragment, Fragment.id == Consensus.fragment_id).filter(Consensus.pair == pair, Consensus.status == status, Consensus.translation != "").order_by(Consensus.id.desc()).limit(300).all()
    return [{**frag_dict(f, media_docs(s)), "translation": c.translation, "confirmed": c.confirmed, "status": c.status, "expert": c.expert, "comments": cm.get(f.id, 0),
             "variants": variants(f.id) if status != "confirmed" else []}
            for c, f in rows if not q or nrm(q) in nrm(f.text_ba + " " + c.translation)]

# ---- комментарии к фрагментам и переводам: любой вошедший ----
@router.get("/fragments/{fid}/comments")
def comments(fid: int, u: User = Depends(current_user), s: Session = Depends(db)):
    rows = s.query(FComment).filter_by(fragment_id=fid).order_by(FComment.id).all()
    us = {x.id: x for x in s.query(User).filter(User.id.in_({r.user_id for r in rows} or [0]))}
    # уровень рядом с ником показывает опытность комментатора в вопросах перевода
    return [{"id": r.id, "text": r.text, "author": us[r.user_id].name, "role": us[r.user_id].role,
             "level": us[r.user_id].xp // 500 + 1, "mine": r.user_id == u.id, "at": r.created_at.isoformat()} for r in rows]

@router.post("/fragments/{fid}/comments")
def add_comment(fid: int, d: CommentIn, u: User = Depends(current_user), s: Session = Depends(db)):
    limiter.hit(f"cm:{u.id}", 10, 60)
    if not s.get(Fragment, fid): raise HTTPException(404, "Фрагмент не найден")
    s.add(FComment(fragment_id=fid, user_id=u.id, text=clean(d.text, "Комментарий", 500))); s.commit()
    return {"ok": True}

@router.delete("/comments/{cid}")
def del_comment(cid: int, u: User = Depends(current_user), s: Session = Depends(db)):
    c = s.get(FComment, cid)
    if not c: raise HTTPException(404, "Не найдено")
    if c.user_id != u.id and u.role not in STAFF: raise HTTPException(403, "Недостаточно прав")
    s.delete(c); audit(s, u.id, "comment_deleted", str(cid)); s.commit()
    return {"ok": True}

# ---- эксперты: спорные случаи ----
@router.get("/expert/queue")
def queue(u: User = Depends(require(*STAFF)), s: Session = Depends(db)):
    out = []
    md = media_docs(s)
    for c, f in s.query(Consensus, Fragment).join(Fragment, Fragment.id == Consensus.fragment_id).filter(Consensus.status == "expert_review").limit(100):
        g = {}
        for (t,) in s.query(Answer.text).filter(Answer.fragment_id == f.id, Answer.pair == c.pair, Answer.text != ""):
            x = g.setdefault(nrm(t), [t, 0]); x[1] += 1
        n = sum(v[1] for v in g.values()) or 1
        out.append({**frag_dict(f, md), "pair": c.pair, "variants": sorted(([v[0], v[1], round(100 * v[1] / n)] for v in g.values()), key=lambda v: -v[1])})
    return out

@router.post("/expert/{fid}/decide")
def decide(fid: int, d: DecideIn, u: User = Depends(require("expert", "admin")), s: Session = Depends(db)):
    pair_ok(d.pair)
    c = s.query(Consensus).filter_by(fragment_id=fid, pair=d.pair).first()
    if not c: raise HTTPException(404, "Нет такого случая")
    c.translation, c.status, c.expert = clean(d.translation, "Перевод", 400), "confirmed", True
    audit(s, u.id, "expert_decision", f"fragment={fid} pair={d.pair}"); s.commit()
    return {"ok": True}

# ---- материалы: нарезка и загрузка ----
def add_fragment(s, text, doc, chapter, pos, a_from=None, a_to=None, auto=None):
    f = Fragment(text_ba=text, source_doc=doc, chapter=chapter, position=pos, audio_from=a_from, audio_to=a_to)
    s.add(f); s.flush()
    for p, v in (auto or {}).items():
        if p in PAIRS and v.get("text"): s.add(AutoTr(fragment_id=f.id, pair=p, text=v["text"][:600], wrong=v.get("wrong", "")[:600]))
    return f

# Нарезка аудио: строки расшифровки с отметкой времени, например
#   00:00 Беренсе һөйләм.
#   0:07  Икенсе һөйләм.
# Конец отрезка — начало следующей строки (у последней + 15 секунд).
TC = re.compile(r"^\s*\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?\s*[-–—]?\s*(.+?)\s*$")

def parse_timecodes(text):
    out = []
    for line in text.splitlines():
        m = TC.match(line)
        if not m: continue
        h, mm, ss, body = m.groups()
        t = int(h) * 3600 + int(mm) * 60 + int(ss) if ss else int(h) * 60 + int(mm)
        if len(body) >= 3: out.append([t, body])
    out.sort(key=lambda x: x[0])
    return [(t, out[i + 1][0] if i + 1 < len(out) else t + 15, b) for i, (t, b) in enumerate(out)]

@router.post("/admin/slice")
def slice_text(d: SliceIn, u: User = Depends(require("admin", "teacher")), s: Session = Depends(db)):
    doc = clean(d.source_doc, "Источник", 200)
    if d.mode == "audio":
        rows = parse_timecodes(d.text)
        if not rows: raise HTTPException(400, "Не нашла строк с отметкой времени — нужен формат «00:07 текст»")
        if not s.query(Media).filter_by(doc=doc).first(): raise HTTPException(400, "Сначала загрузите аудиофайл для этого источника")
        n, skipped = 0, 0
        for i, (a, b, body) in enumerate(rows):
            if not 3 <= len(body) <= 400: continue
            if not_bashkir(body): skipped += 1; continue      # латиница в задания не попадает
            add_fragment(s, body, doc, d.chapter, i + 1, a, b); n += 1
        audit(s, u.id, "slice_audio", f"{doc}: {n}"); s.commit()
        if not n: raise HTTPException(400, "Ни одной строки на башкирской кириллице — проверьте текст расшифровки")
        return {"fragments": n, "skipped": skipped}
    parts = re.split(r"\n\s*\n", d.text) if d.mode == "paragraph" else re.split(r"(?<=[.!?…])\s+", " ".join(d.text.split()))
    n = 0
    skipped = 0
    for i, p in enumerate(x.strip() for x in parts):
        if not 12 <= len(p) <= 400: continue
        if not_bashkir(p): skipped += 1; continue
        add_fragment(s, p, doc, d.chapter, i + 1); n += 1
    audit(s, u.id, "slice", f"{doc}: {n}"); s.commit()
    return {"fragments": n, "skipped": skipped}

@router.post("/admin/fragments")
def import_fragments(items: list[FragIn], u: User = Depends(require("admin")), s: Session = Depends(db)):
    for i in items[:2000]: add_fragment(s, clean(i.text_ba, "Текст", 600), i.source_doc, i.chapter, i.position, i.audio_from, i.audio_to, i.auto)
    audit(s, u.id, "fragments_import", str(len(items))); s.commit()
    return {"added": len(items[:2000])}

# ---- API и выгрузка (по ключу X-API-Key = env API_KEY или для персонала) ----
def api_access(request: Request, authorization, s):
    key = os.getenv("API_KEY")
    if key and secrets.compare_digest(request.headers.get("x-api-key", ""), key): return
    current = current_user(authorization, s)
    if current.role not in STAFF: raise HTTPException(403, "Нужен API-ключ или роль персонала")

@router.get("/v1/export")
def export(request: Request, pair: str = "ba-ru", format: str = "json", authorization: str | None = Header(default=None), s: Session = Depends(db)):
    api_access(request, authorization, s); pair_ok(pair)
    rows = s.query(Consensus, Fragment).join(Fragment, Fragment.id == Consensus.fragment_id).filter(Consensus.pair == pair, Consensus.status.in_(("confirmed", "expert_review"))).all()
    data = [{"fragment_id": f.id, "text_ba": f.text_ba, "lang_pair": pair, "translation": c.translation,
             "source": {"doc": f.source_doc, "chapter": f.chapter, "position": f.position, "audio_from": f.audio_from, "audio_to": f.audio_to},
             "confirmed": c.confirmed, "status": c.status} for c, f in rows]
    if format == "csv":
        o = io.StringIO(); w = csv.writer(o); w.writerow(["fragment_id", "text_ba", "lang_pair", "translation", "source", "confirmed", "status"])
        for x in data: w.writerow([x["fragment_id"], x["text_ba"], pair, x["translation"], f'{x["source"]["doc"]}; {x["source"]["chapter"]}; №{x["source"]["position"]}', x["confirmed"], x["status"]])
        return Response(o.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=tamga_{pair}.csv"})
    return data

@router.get("/v1/fragments")
def api_fragments(request: Request, limit: int = Query(50, le=200), offset: int = 0, authorization: str | None = Header(default=None), s: Session = Depends(db)):
    api_access(request, authorization, s)
    return [frag_dict(f, media_docs(s)) for f in s.query(Fragment).order_by(Fragment.id).offset(offset).limit(limit)]

# ---- учитель: отчёт по классу (LMS-совместимость) ----
@router.get("/teacher/report")
def report(format: str = "json", u: User = Depends(require("teacher", "admin")), s: Session = Depends(db)):
    rows = class_report(s, u)
    if format == "csv":   # для электронного журнала / LMS: открывается в Excel
        o = io.StringIO(); w = csv.writer(o, delimiter=";")
        w.writerow(["Ученик", "Уровень", "Ответов", "Исправлено подставных ошибок", "Пропущено ошибок", "XP", "Серия, дней", "Последняя активность"])
        for r in rows: w.writerow([r["name"], r["level"], r["answers"], r["fixes"], r["errors"], r["xp"], r["streak"], r["last"]])
        return Response("\ufeff" + o.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=class_report.csv"})
    return rows

def class_report(s, u):
    if not u.school_id or not u.grade: return []
    st = s.query(User).filter_by(role="student", blocked=False, school_id=u.school_id, grade=u.grade, letter=u.letter).all()
    out = []
    for x in st:
        A = s.query(Answer).filter_by(user_id=x.id).all()
        # уровень рядом с именем показывает, насколько усердно ученик занимался
        out.append({"name": x.name, "level": x.xp // 500 + 1, "answers": len(A), "fixes": sum(a.fixed for a in A),
                    "errors": sum(a.error for a in A), "xp": x.xp, "streak": live_streak(x), "last": str(x.last_active or "")})
    return sorted(out, key=lambda r: -r["xp"])

# ---- рейтинги ----
@router.get("/rating")
def rating(scope: str = "all", period: str = "all", metric: str = "points", u: User = Depends(current_user), s: Session = Depends(db)):
    today = dt.date.today()
    since = {"day": today, "week": today - dt.timedelta(days=6), "month": today - dt.timedelta(days=29), "year": today - dt.timedelta(days=364)}.get(period)
    q = s.query(User).filter_by(role="student", blocked=False)
    if scope == "school":
        if not u.school_id: return {"need_school": True, "rows": []}
        q = q.filter_by(school_id=u.school_id)
    elif scope == "class":
        if not (u.school_id and u.grade): return {"need_school": True, "rows": []}
        q = q.filter_by(school_id=u.school_id, grade=u.grade, letter=u.letter)
    users = q.all()
    aq = s.query(Answer).filter(Answer.user_id.in_([x.id for x in users] or [0]))
    if since: aq = aq.filter(Answer.day >= since)
    A = {}
    for a in aq: A.setdefault(a.user_id, []).append(a)
    frs = {f.id: set(nrm(f.text_ba).split()) for f in s.query(Fragment).filter(Fragment.id.in_({a.fragment_id for l in A.values() for a in l} or [0]))}
    rows = []
    for x in users:
        l = A.get(x.id, [])
        if not l: continue
        m = {"points": sum(a.xp for a in l), "vocab": len(set().union(*[frs.get(a.fragment_id, set()) for a in l])),
             "fixes": sum(a.fixed for a in l), "errors": sum(a.error for a in l), "n": len(l)}
        rows.append({"name": x.name, "sub": x.class_name or "", "school_id": x.school_id, "me": x.id == u.id, **m})
    if scope == "schools":
        g = {}
        names = {sc.id: f"{sc.name} · {sc.city}" for sc in s.query(School)}
        for r in rows:
            if r["school_id"]:
                t = g.setdefault(r["school_id"], {"name": names.get(r["school_id"], "?"), "sub": "", "points": 0, "vocab": 0, "fixes": 0, "errors": 0, "n": 0})
                for k in ("points", "vocab", "fixes", "errors", "n"): t[k] += r[k]
        rows = list(g.values())
    if metric == "clean": rows = [r for r in rows if r["n"] >= 5]; rows.sort(key=lambda r: (r["errors"], -r["n"]))
    else: rows.sort(key=lambda r: -r.get({"points": "points", "vocab": "vocab", "fixes": "fixes"}.get(metric, "points"), 0))
    key = {"vocab": "vocab", "fixes": "fixes", "clean": "errors"}.get(metric, "points")
    return {"rows": [{"rank": i + 1, "name": r["name"], "sub": r["sub"], "value": r[key], "me": r.get("me", False)} for i, r in enumerate(rows[:50])]}


# ---- настройки для клиента ----
@router.get("/config")
def config():
    return {"goal": DAILY, "min_voters": MIN_VOTERS, "noise": round(NOISE * 100), "share": round(SHARE * 100), "tts": tts.available() or tts.has_pack(), "asr": asr.available(), "pauses": asr.can_pauses(), "bot": os.getenv("BOT_USERNAME", "").lstrip("@")}

# ---- озвучка башкирского фрагмента (TTS) ----
import tts

@router.get("/tts/{fid}")
def speak(fid: int, request: Request, s: Session = Depends(db)):
    limiter.hit("tts:" + ip_of(request), 30, 60)
    f = s.get(Fragment, fid)
    if not f: raise HTTPException(404, "Фрагмент не найден")
    path = tts.synth(f.text_ba)
    if not path: raise HTTPException(503, "Серверная озвучка не установлена")
    return Response(path.read_bytes(), media_type="audio/wav", headers={"Cache-Control": "public, max-age=604800"})

# ---- живой голос: учитель или эксперт записывает фрагмент, запись звучит вместо синтеза ----
AUDIO = Path(os.getenv("AUDIO_DIR", Path(__file__).parent / "data" / "audio"))

# Запись голоса не звучит в заданиях сразу: записать можно что угодно. Сначала её слушают
# и оценивают ученики, потом утверждает эксперт — и только после этого она заменяет синтез.
@router.post("/fragments/{fid}/audio")
async def upload_audio(fid: int, request: Request, u: User = Depends(require("teacher", "moderator", "expert", "admin")), s: Session = Depends(db)):
    if not s.get(Fragment, fid): raise HTTPException(404, "Фрагмент не найден")
    data = await request.body()
    if not 1000 < len(data) < 3_000_000: raise HTTPException(400, "Запись слишком короткая или длиннее ~1 минуты")
    AUDIO.mkdir(parents=True, exist_ok=True)
    for old in s.query(VoiceRec).filter_by(fragment_id=fid, user_id=u.id).filter(VoiceRec.status.in_(("voting", "expert"))):
        old.status = "rejected"                                  # новая запись того же автора заменяет прежнюю
    r = VoiceRec(fragment_id=fid, user_id=u.id, token=secrets.token_urlsafe(18))
    (AUDIO / f"rec_{r.token}.webm").write_bytes(data)
    s.add(r); audit(s, u.id, "audio_recorded", str(fid)); s.commit()
    return {"ok": True, "status": "voting"}

@router.get("/rec/{token}")
def rec_file(token: str, s: Session = Depends(db)):
    r = s.query(VoiceRec).filter_by(token=token).first()
    p = AUDIO / f"rec_{token}.webm"
    if not r or r.status == "rejected" or not p.exists(): raise HTTPException(404, "Записи нет")
    return FileResponse(p, media_type="audio/webm")

class VoteIn(BaseModel): ok: bool

@router.post("/rec/{rid}/vote")
def rec_vote(rid: int, d: VoteIn, u: User = Depends(current_user), s: Session = Depends(db)):
    limiter.hit(f"recvote:{u.id}", 40, 60)
    r = s.get(VoiceRec, rid)
    if not r or r.status != "voting": raise HTTPException(404, "Эта запись уже не на голосовании")
    if r.user_id == u.id: raise HTTPException(400, "За свою запись голосовать нельзя")
    if s.query(VoiceVote).filter_by(rec_id=rid, user_id=u.id).first(): raise HTTPException(409, "Вы уже голосовали")
    s.add(VoiceVote(rec_id=rid, user_id=u.id, ok=d.ok)); s.flush()
    votes = [v.ok for v in s.query(VoiceVote).filter_by(rec_id=rid)]
    if len(votes) >= MIN_VOTERS:
        yes = sum(votes) / len(votes)
        if yes >= SHARE: r.status = "expert"                     # ученики одобрили — дальше решает эксперт
        elif yes < 0.5: r.status = "rejected"
    s.commit()
    return {"status": r.status, "votes": len(votes)}

@router.get("/expert/recs")
def rec_queue(u: User = Depends(require("moderator", "expert", "admin")), s: Session = Depends(db)):
    out = []
    for r in s.query(VoiceRec).filter(VoiceRec.status.in_(("expert", "voting"))).order_by(VoiceRec.status, VoiceRec.id):
        f, au = s.get(Fragment, r.fragment_id), s.get(User, r.user_id)
        votes = [v.ok for v in s.query(VoiceVote).filter_by(rec_id=r.id)]
        if f: out.append({"id": r.id, "token": r.token, "status": r.status, "text_ba": f.text_ba, "author": au.name if au else "",
                          "yes": sum(votes), "no": len(votes) - sum(votes), "need": MIN_VOTERS})
    return out

@router.post("/rec/{rid}/decide")
def rec_decide(rid: int, d: VoteIn, u: User = Depends(require("expert", "admin")), s: Session = Depends(db)):
    r = s.get(VoiceRec, rid)
    if not r or r.status != "expert": raise HTTPException(400, "Запись ещё не прошла голосование учеников")
    if d.ok:
        (AUDIO / f"{r.fragment_id}.webm").write_bytes((AUDIO / f"rec_{r.token}.webm").read_bytes())
        r.status = "approved"
    else: r.status = "rejected"
    audit(s, u.id, "audio_" + r.status, str(r.fragment_id)); s.commit()
    return {"status": r.status}

AUDIO_TYPES = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/aac": ".m4a",
               "audio/ogg": ".ogg", "audio/webm": ".webm", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/flac": ".flac"}

@router.post("/admin/cleanup")
def cleanup_latin(u: User = Depends(require("admin", "teacher")), s: Session = Depends(db)):
    """Прячет из заданий фрагменты, записанные латиницей (например, машинной расшифровкой).
    Фрагменты не удаляются: собранные по ним переводы и статистика остаются."""
    n = 0
    for f in s.query(Fragment).filter_by(active=True):
        if not_bashkir(f.text_ba): f.active = False; n += 1
    audit(s, u.id, "cleanup_latin", str(n)); s.commit()
    return {"hidden": n}

@router.post("/admin/audio")
async def upload_media(request: Request, doc: str = Query(max_length=200), u: User = Depends(require("admin", "teacher")), s: Session = Depends(db)):
    """Аудиоисточник (аудиокнига, радиопередача): файл целиком, фрагменты ссылаются на него отрезками времени."""
    mime = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    ext = AUDIO_TYPES.get(mime)
    if not ext: raise HTTPException(400, "Нужен аудиофайл: mp3, m4a, ogg, wav, flac или webm")
    data = await request.body()
    if not 2000 < len(data) < 60_000_000: raise HTTPException(400, "Файл пустой или больше ~60 МБ")
    doc = clean(doc, "Источник", 200)
    AUDIO.mkdir(parents=True, exist_ok=True)
    m = s.query(Media).filter_by(doc=doc).first() or Media(doc=doc)
    m.filename, m.mime = f"src_{hashlib.sha256(doc.encode()).hexdigest()[:16]}{ext}", mime
    (AUDIO / m.filename).write_bytes(data)
    s.add(m); _MD["t"] = 0.0
    audit(s, u.id, "audio_source", f"{doc}: {len(data) // 1024} КБ"); s.commit()
    return {"ok": True, "doc": doc, "fragments": s.query(Fragment).filter_by(source_doc=doc).count()}

class TranscribeIn(BaseModel):
    doc: str = Field(max_length=200); mode: str = "asr"; text: str = Field(default="", max_length=200000)

# Расшифровка идёт долго (на запись в пять минут уходит несколько минут работы), поэтому она
# выполняется в фоне: сайт сразу отдаёт номер задания, а страница спрашивает о ходе работы.
JOBS: dict[str, dict] = {}

def run_job(jid, path, mode, text):
    j = JOBS[jid]
    try:
        if mode == "pauses":
            rows = asr.by_pauses(path, text)
        else:
            j.update(stage="load"); asr._load()        # первая расшифровка скачивает модель — это долго
            j.update(stage="work"); rows = asr.transcribe(path, lambda p: j.update(progress=p))
        if not rows: raise RuntimeError("В записи не нашлось речи")
        txt = asr.as_lines(rows)
        j.update(state="done", text=txt, lines=len(rows), progress=1.0, note=asr.alphabet_note(txt, mode))
    except Exception as ex:
        why, raw = asr.explain(ex)
        log.warning("Расшифровка не удалась (%s): %s", mode, raw)
        j.update(state="error", error=f"Не получилось: {why}", raw=raw)

@router.post("/admin/transcribe")
def transcribe_media(d: TranscribeIn, u: User = Depends(require("admin", "teacher")), s: Session = Depends(db)):
    """Запускает автоматическую разметку аудио и возвращает номер задания."""
    m = s.query(Media).filter_by(doc=clean(d.doc, "Источник", 200)).first()
    if not m or not (AUDIO / m.filename).exists(): raise HTTPException(404, "Сначала загрузите аудиофайл для этого источника")
    if d.mode == "pauses":
        if not asr.can_pauses(): raise HTTPException(503, "Чтение аудио не установлено: запустите install_asr.bat")
    elif not asr.available():
        raise HTTPException(503, "Распознавание речи не установлено: install_asr.bat (быстрая модель) или install_asr_ba.bat (башкирская)")
    for k, v in list(JOBS.items()):                                   # прибираем старые задания
        if time.time() - v.get("started", 0) > 3600: JOBS.pop(k, None)
    if sum(1 for v in JOBS.values() if v["state"] == "run") >= 2: raise HTTPException(429, "Уже идёт разметка, дождитесь её окончания")
    jid = secrets.token_urlsafe(8)
    JOBS[jid] = {"state": "run", "stage": "work", "progress": 0.0, "started": time.time(), "text": "", "lines": 0, "error": ""}
    audit(s, u.id, "transcribe", f"{m.doc}: {d.mode}"); s.commit()
    threading.Thread(target=run_job, args=(jid, AUDIO / m.filename, d.mode, d.text), daemon=True).start()
    return {"job": jid}

@router.get("/admin/transcribe/{jid}")
def transcribe_status(jid: str, u: User = Depends(require("admin", "teacher"))):
    j = JOBS.get(jid)
    if not j: raise HTTPException(404, "Задание не найдено — попробуйте ещё раз")
    return {k: v for k, v in j.items() if k != "started"}

@router.get("/admin/asr-check")
def asr_check(u: User = Depends(require("admin", "teacher"))):
    """Проверка распознавания: что установлено, скачана ли модель, в чём ошибка."""
    return asr.check()

@router.get("/admin/media-info")
def media_info(doc: str = Query(max_length=200), u: User = Depends(require("admin", "teacher")), s: Session = Depends(db)):
    m = s.query(Media).filter_by(doc=clean(doc, "Источник", 200)).first()
    if not m: raise HTTPException(404, "Сначала загрузите аудиофайл для этого источника")
    return {"file": m.filename}

@router.get("/msrc/{name}")
def media_src(name: str, s: Session = Depends(db)):
    """Аудиоисточник целиком — для проверки расшифровки на слух перед нарезкой."""
    m = s.query(Media).filter_by(filename=name).first()
    if not m or not (AUDIO / m.filename).exists(): raise HTTPException(404, "Аудиоисточника нет")
    return FileResponse(AUDIO / m.filename, media_type=m.mime)

@router.get("/media/{fid}")
def get_media(fid: int, s: Session = Depends(db)):
    """Аудиофайл источника, из которого нарезан фрагмент (браузер сам перематывает на нужную секунду)."""
    f = s.get(Fragment, fid)
    m = s.query(Media).filter_by(doc=f.source_doc).first() if f else None
    if not m or not (AUDIO / m.filename).exists(): raise HTTPException(404, "Аудиоисточника нет")
    return FileResponse(AUDIO / m.filename, media_type=m.mime)

@router.get("/audio/{fid}")
def get_audio(fid: int):
    p = AUDIO / f"{fid}.webm"
    if not p.exists(): raise HTTPException(404, "Записи нет")
    return Response(p.read_bytes(), media_type="audio/webm")

# ---- жалоба на задание: «фраза и перевод не совпадают» ----
REPORTS_TO_HIDE = int(os.getenv("REPORTS_TO_HIDE", "3"))

@router.post("/fragments/{fid}/report")
def report_fragment(fid: int, u: User = Depends(current_user), s: Session = Depends(db)):
    limiter.hit(f"rep:{u.id}", 20, 600)
    f = s.get(Fragment, fid)
    if not f: raise HTTPException(404, "Фрагмент не найден")
    if s.query(Audit).filter_by(user_id=u.id, action="report", detail=str(fid)).first():
        raise HTTPException(409, "Вы уже пожаловались на это задание")
    audit(s, u.id, "report", str(fid))
    n = s.query(Audit).filter_by(action="report", detail=str(fid)).count() + 1
    hidden = u.role in STAFF or n >= REPORTS_TO_HIDE     # персонал скрывает сразу
    if hidden:
        f.active = False
        s.query(Shown).filter_by(fragment_id=fid).delete()
    s.commit()
    return {"ok": True, "hidden": hidden, "reports": n}
