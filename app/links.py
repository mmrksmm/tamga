"""Связь сайта и Telegram-бота, коды классов от учителя."""
import os, secrets, hashlib, datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models import User, School, OneTimeCode, ClassInvite, TgUser, now
from security import db, current_user, require, new_token, limiter, ip_of, audit

router = APIRouter(prefix="/api")
ALPHA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # без похожих символов 0/O, 1/I/L
_h = lambda c: hashlib.sha256(c.strip().upper().encode()).hexdigest()
BOT = os.getenv("BOT_USERNAME", "").lstrip("@")

def rand_code(n=8): return "".join(secrets.choice(ALPHA) for _ in range(n))

def make_code(s, kind, user_id, minutes=15):
    raw = rand_code()
    s.query(OneTimeCode).filter(OneTimeCode.expires_at < now()).delete()
    s.add(OneTimeCode(code_hash=_h(raw), kind=kind, user_id=user_id, expires_at=now() + dt.timedelta(minutes=minutes))); s.commit()
    return raw

def use_code(s, kind, raw):
    c = s.get(OneTimeCode, _h(raw or ""))
    if not c or c.kind != kind or c.expires_at < now(): return None
    u = s.get(User, c.user_id); s.delete(c); s.commit()
    return u if u and not u.blocked else None

def find_invite(s, code):
    return s.get(ClassInvite, (code or "").strip().upper()) if code and code.strip() else None

def apply_invite(s, u, inv):
    sc = s.get(School, inv.school_id)
    u.school_id, u.school, u.grade, u.letter = inv.school_id, sc.name if sc else "", inv.grade, inv.letter
    u.class_name = f"{inv.grade}{inv.letter}"

class CodeIn(BaseModel): code: str = Field(max_length=20)

@router.post("/tg/link-code")
def tg_link_code(u: User = Depends(current_user), s: Session = Depends(db)):
    """Код для привязки Telegram к аккаунту сайта: ссылка t.me/<бот>?start=link_<код>."""
    raw = make_code(s, "tg_link", u.id, 15)
    return {"code": raw, "bot": BOT, "link": f"https://t.me/{BOT}?start=link_{raw}" if BOT else ""}

@router.post("/tg/login")
def tg_login(d: CodeIn, request: Request, s: Session = Depends(db)):
    """Вход на сайт по одноразовой ссылке из бота."""
    limiter.hit("tglogin:" + ip_of(request), 10, 600)
    u = use_code(s, "site_login", d.code)
    if not u: raise HTTPException(400, "Ссылка для входа устарела — запросите новую в боте")
    audit(s, u.id, "login_tg"); s.commit()
    from api import user_dict
    return {"token": new_token(s, u), "user": user_dict(u)}

@router.get("/tg/status")
def tg_status(u: User = Depends(current_user), s: Session = Depends(db)):
    return {"linked": s.query(TgUser).filter_by(user_id=u.id).first() is not None, "bot": BOT}

@router.post("/teacher/invite")
def teacher_invite(u: User = Depends(require("teacher", "admin")), s: Session = Depends(db)):
    if not (u.school_id and u.grade): raise HTTPException(400, "Сначала укажите свою школу и класс в настройках")
    inv = s.query(ClassInvite).filter_by(teacher_id=u.id, school_id=u.school_id, grade=u.grade, letter=u.letter).first()
    if not inv:
        inv = ClassInvite(code=rand_code(6), teacher_id=u.id, school_id=u.school_id, grade=u.grade, letter=u.letter)
        s.add(inv); audit(s, u.id, "class_invite", inv.code); s.commit()
    return {"code": inv.code, "class_name": f"{inv.grade}{inv.letter}", "bot": BOT}

@router.post("/me/class-code")
def join_class(d: CodeIn, u: User = Depends(current_user), s: Session = Depends(db)):
    inv = find_invite(s, d.code)
    if not inv: raise HTTPException(400, "Код класса не найден — проверьте его у учителя")
    apply_invite(s, u, inv); s.commit()
    from api import user_dict
    return user_dict(u)
