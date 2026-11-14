"""API: вход, аккаунт, рейтинг, роли и администрирование."""
import re, secrets, random, datetime as dt
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import *
from security import *

router = APIRouter(prefix="/api")
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
CYR = re.compile(r"[А-Яа-яЁёӘәӨөҮүҒғҠҡҢңҪҫҺһҘҙ]")
BAD = re.compile(r"https?://|www\.|<[^>]+>", re.I)

def norm(t): return " ".join(t.lower().split())

def clean(text, label, mx=300):
    t = " ".join(text.split())
    if not t: raise HTTPException(400, f"Поле «{label}» пустое")
    if len(t) > mx: raise HTTPException(400, f"Поле «{label}» длиннее {mx} символов")
    if BAD.search(t): raise HTTPException(400, "Ссылки и HTML-теги запрещены")
    return t

# ---------- схемы ----------
class AuthIn(BaseModel):
    email: str = Field(max_length=160, pattern=EMAIL)
    password: str = Field(max_length=128)
class RegisterIn(AuthIn):
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)
    school: str = Field(default="", max_length=120)
    class_name: str = Field(default="", max_length=30)
class AnswerIn(BaseModel): answer: str = Field(max_length=300)
class TranslationIn(BaseModel):
    original: str; proposed: str; context: str = Field(default="Общий", max_length=120)
class VoteIn(BaseModel): choice: str
class ReviewIn(BaseModel): status: str; note: str = Field(default="", max_length=500)
class DeleteIn(BaseModel): password: str
class UserPatch(BaseModel): role: str | None = None; blocked: bool | None = None; school: str | None = None; class_name: str | None = None
class TaskIn(BaseModel):
    prompt: str = Field(max_length=300); answer: str = Field(max_length=300)
    accepted: str = Field(default="", max_length=600); explanation: str = Field(default="", max_length=500)
    level: str = Field(default="A1", max_length=10); category: str = Field(default="Повседневное", max_length=60)

def live_streak(u):
    # серия сгорает, если вчера дневная норма не выполнена
    return u.streak if u.last_active and u.last_active >= dt.date.today() - dt.timedelta(days=1) else 0

def user_dict(u): return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "xp": u.xp,
                          "streak": live_streak(u), "streak_today": u.last_active == dt.date.today(),
                          "school": u.school, "class_name": u.class_name, "pair": u.pair or "ba-ru"}

def touch_streak(u):
    today = dt.date.today()
    if u.last_active == today: return
    u.streak = u.streak + 1 if u.last_active == today - dt.timedelta(days=1) else 1
    u.last_active = today

# ---------- вход и аккаунт ----------
@router.post("/login")
def login(data: AuthIn, request: Request, s: Session = Depends(db)):
    email = data.email.lower()
    limiter.hit("login-ip:" + ip_of(request), 20, 600)
    limiter.hit("login-mail:" + email, 8, 600)  # защита от подбора пароля к одному аккаунту
    u = s.query(User).filter_by(email=email).first()
    ok = check_pw(u.password if u else DUMMY_HASH, data.password)  # одинаковое время ответа
    if not u or not ok:
        audit(s, u.id if u else None, "login_failed", email); s.commit()
        raise HTTPException(401, "Неверный email или пароль")
    if u.blocked: raise HTTPException(403, "Аккаунт заблокирован")
    audit(s, u.id, "login"); s.commit()
    return {"token": new_token(s, u), "user": user_dict(u)}

@router.get("/me")
def me(u: User = Depends(current_user)): return user_dict(u)

@router.post("/logout")
def logout(authorization: str | None = Header(default=None), s: Session = Depends(db)):
    if authorization and authorization.startswith("Bearer "): drop_token(s, authorization[7:])
    return {"ok": True}

@router.post("/logout-all")
def logout_all(u: User = Depends(current_user), s: Session = Depends(db)):
    s.query(SessionToken).filter_by(user_id=u.id).delete(); s.commit()
    return {"ok": True}

@router.delete("/me")
def delete_me(data: DeleteIn, u: User = Depends(current_user), s: Session = Depends(db)):
    if not check_pw(u.password, data.password): raise HTTPException(403, "Неверный пароль")
    if u.role == "admin" and s.query(User).filter_by(role="admin", blocked=False).count() < 2:
        raise HTTPException(400, "Нельзя удалить единственного администратора")
    s.query(SessionToken).filter_by(user_id=u.id).delete()
    s.query(Vote).filter_by(user_id=u.id).delete()
    u.name, u.email, u.password, u.blocked = "Удалённый пользователь", f"deleted-{u.id}-{secrets.token_hex(4)}@invalid", "!", True
    u.school = u.class_name = ""
    audit(s, u.id, "account_deleted"); s.commit()
    return {"ok": True}

# ---------- обучение ----------
@router.get("/dashboard")
def dashboard(u: User = Depends(current_user), s: Session = Depends(db)):
    total = s.query(Attempt).filter_by(user_id=u.id).count()
    good = s.query(Attempt).filter_by(user_id=u.id, correct=True).count()
    today = dt.date.today()
    weekly = [s.query(Attempt).filter_by(user_id=u.id, correct=True, day=today - dt.timedelta(days=6 - i)).count() for i in range(7)]
    return {"user": user_dict(u), "approved_count": s.query(Translation).filter_by(status="approved").count(),
            "my_translations": s.query(Translation).filter_by(author_id=u.id).count(),
            "tasks_done": s.query(func.count(func.distinct(Attempt.task_id))).filter_by(user_id=u.id, correct=True).scalar(),
            "accuracy": round(100 * good / total) if total else 0, "weekly": weekly}

@router.get("/tasks")
def tasks(s: Session = Depends(db), u: User = Depends(current_user)):
    rows = s.query(Task).filter_by(active=True).all()
    out = []
    for t in rows:  # правильный ответ клиенту не отдаём — только варианты
        pool = list({x.answer for x in rows if x.id != t.id and x.direction == t.direction and norm(x.answer) != norm(t.answer)})
        opts = [t.answer] + random.sample(pool, min(3, len(pool)))
        random.shuffle(opts)
        out.append({"id": t.id, "prompt": t.prompt, "direction": t.direction, "level": t.level, "category": t.category, "options": opts})
    return out

@router.post("/tasks/{task_id}/answer")
def answer(task_id: int, data: AnswerIn, u: User = Depends(current_user), s: Session = Depends(db)):
    limiter.hit(f"ans:{u.id}", 30, 60)
    t = s.get(Task, task_id)
    if not t or not t.active: raise HTTPException(404, "Задание не найдено")
    valid = {norm(t.answer)} | {norm(x) for x in t.accepted.splitlines() if x.strip()}
    ok = norm(data.answer) in valid
    today = dt.date.today()
    first_today = ok and not s.query(Attempt).filter_by(user_id=u.id, task_id=t.id, correct=True, day=today).first()
    s.add(Attempt(user_id=u.id, task_id=t.id, correct=ok, day=today))
    if ok: touch_streak(u)
    if first_today: u.xp += 10  # XP за одно задание — один раз в день, повторы не фармятся
    s.commit()
    return {"correct": ok, "expected": t.answer, "explanation": t.explanation, "xp_awarded": 10 if first_today else 0}

# ---------- переводы ----------
STAFF = ("moderator", "expert", "admin")

def votes_for(s, ids):
    res = {i: {"accurate": 0, "inaccurate": 0} for i in ids}
    for tid, ch, n in s.query(Vote.translation_id, Vote.choice, func.count()).filter(Vote.translation_id.in_(ids or [0])).group_by(Vote.translation_id, Vote.choice):
        res[tid][ch] = n
    return res

@router.get("/translations")
def translations(status: str | None = None, s: Session = Depends(db), u: User = Depends(current_user)):
    q = s.query(Translation)
    if status: q = q.filter_by(status=status)
    if u.role not in STAFF: q = q.filter((Translation.status != "rejected") | (Translation.author_id == u.id))
    rows = q.order_by(Translation.id.desc()).limit(200).all()
    v = votes_for(s, [x.id for x in rows])
    names = {x.id: x.name for x in s.query(User).filter(User.id.in_({r.author_id for r in rows} or [0]))}
    return [{"id": x.id, "original": x.original, "proposed": x.proposed, "status": x.status, "context": x.context, "note": x.note,
             "votes": v[x.id]["accurate"], "against": v[x.id]["inaccurate"], "author": names.get(x.author_id, "—")} for x in rows]

@router.post("/translations")
def propose(data: TranslationIn, u: User = Depends(current_user), s: Session = Depends(db)):
    orig, prop = clean(data.original, "Исходная фраза"), clean(data.proposed, "Перевод")
    if not CYR.search(prop): raise HTTPException(400, "Перевод должен быть на башкирском (кириллицей)")
    if norm(orig) == norm(prop): raise HTTPException(400, "Перевод совпадает с исходной фразой")
    day_ago = now() - dt.timedelta(days=1)
    if s.query(Translation).filter(Translation.author_id == u.id, Translation.created_at > day_ago).count() >= 20:
        raise HTTPException(429, "Лимит: не больше 20 предложений в сутки")
    dup = [x for x in s.query(Translation).all() if norm(x.original) == norm(orig) and norm(x.proposed) == norm(prop)]
    if dup: raise HTTPException(409, "Такой вариант уже предложен — проголосуйте за него")
    x = Translation(original=orig, proposed=prop, author_id=u.id, context=clean(data.context, "Контекст", 120))
    s.add(x); s.commit(); s.refresh(x)
    return {"id": x.id, "status": x.status}

@router.post("/translations/{tid}/vote")
def vote(tid: int, data: VoteIn, u: User = Depends(current_user), s: Session = Depends(db)):
    limiter.hit(f"vote:{u.id}", 60, 60)
    x = s.get(Translation, tid)
    if not x: raise HTTPException(404, "Перевод не найден")
    if data.choice not in ("accurate", "inaccurate"): raise HTTPException(400, "Некорректный голос")
    if x.status not in ("pending", "review"): raise HTTPException(400, "Голосование по этому переводу закрыто")
    if x.author_id == u.id: raise HTTPException(400, "Нельзя оценивать собственный перевод")
    if s.query(Vote).filter_by(translation_id=tid, user_id=u.id).first(): raise HTTPException(409, "Вы уже голосовали")
    s.add(Vote(translation_id=tid, user_id=u.id, choice=data.choice)); s.flush()
    v = votes_for(s, [tid])[tid]
    # популярность не равна правильности: голоса лишь отправляют вариант к эксперту
    if x.status == "pending" and v["accurate"] >= 3 and v["accurate"] - v["inaccurate"] >= 2: x.status = "review"
    s.commit()
    return {"ok": True, "votes": v["accurate"], "status": x.status}

@router.post("/translations/{tid}/review")
def review(tid: int, data: ReviewIn, u: User = Depends(require(*STAFF)), s: Session = Depends(db)):
    allowed = {"moderator": ("review", "rejected"), "expert": ("approved", "rejected", "review", "archived"),
               "admin": ("approved", "rejected", "review", "archived")}[u.role]
    if data.status not in allowed: raise HTTPException(403, "Эта роль не может установить такой статус")
    x = s.get(Translation, tid)
    if not x: raise HTTPException(404, "Перевод не найден")
    if x.author_id == u.id and u.role != "admin": raise HTTPException(403, "Нельзя проверять собственный перевод")
    if data.status == "rejected" and not data.note.strip(): raise HTTPException(400, "При отклонении укажите причину")
    if data.status == "approved" and x.status != "approved":
        author = s.get(User, x.author_id)
        if author and not author.blocked: author.xp += 20
    x.status, x.note, x.reviewed_by = data.status, data.note.strip(), u.id
    audit(s, u.id, "review", f"translation={tid} status={data.status}"); s.commit()
    return {"ok": True, "status": x.status}

# ---------- публичные данные ----------
@router.get("/leaderboard")
def leaderboard(s: Session = Depends(db), u: User = Depends(current_user)):
    rows = s.query(User).filter_by(role="student", blocked=False).order_by(User.xp.desc()).limit(50).all()
    return [{"rank": i + 1, "name": x.name, "school": x.school or "—", "class_name": x.class_name or "—", "xp": x.xp} for i, x in enumerate(rows)]

def approved(s, q, limit, offset):
    rows = [x for x in s.query(Translation).filter_by(status="approved").order_by(Translation.id).all()
            if norm(q) in norm(x.original + " " + x.proposed + " " + x.context)]
    return rows[offset:offset + limit], len(rows)

@router.get("/dictionary")
def dictionary(request: Request, q: str = Query("", max_length=100), limit: int = Query(100, le=200), offset: int = 0, s: Session = Depends(db)):
    limiter.hit("dict:" + ip_of(request), 60, 60)
    rows, _ = approved(s, q, limit, offset)
    return [{"id": x.id, "original": x.original, "translation": x.proposed, "context": x.context} for x in rows]

@router.get("/v1/translations")
def public_api(request: Request, q: str = Query("", max_length=100), limit: int = Query(50, le=100), offset: int = 0, s: Session = Depends(db)):
    limiter.hit("v1:" + ip_of(request), 60, 60)
    rows, total = approved(s, q, limit, offset)
    return {"items": [{"id": x.id, "original": x.original, "translation": x.proposed, "context": x.context,
                       "source_language": "ru", "target_language": "ba", "verified": True} for x in rows],
            "total": total, "limit": limit, "offset": offset}

# ---------- учитель ----------
@router.get("/teacher/class")
def my_class(u: User = Depends(require("teacher", "admin")), s: Session = Depends(db)):
    rows = s.query(User).filter_by(role="student", school=u.school, class_name=u.class_name, blocked=False).order_by(User.xp.desc()).all()
    return [{"name": x.name, "xp": x.xp, "streak": live_streak(x)} for x in rows] if u.school else []

# ---------- администратор ----------
@router.get("/stats")
def stats(u: User = Depends(require(*STAFF)), s: Session = Depends(db)):
    c = lambda st: s.query(Translation).filter_by(status=st).count()
    return {"users": s.query(User).count(), "translations": s.query(Translation).count(),
            "approved": c("approved"), "pending": c("pending"), "review": c("review")}

@router.get("/admin/users")
def admin_users(u: User = Depends(require("admin")), s: Session = Depends(db)):
    return [{**user_dict(x), "blocked": x.blocked} for x in s.query(User).order_by(User.id).limit(500).all()]

@router.patch("/admin/users/{uid}")
def admin_patch_user(uid: int, data: UserPatch, u: User = Depends(require("admin")), s: Session = Depends(db)):
    x = s.get(User, uid)
    if not x: raise HTTPException(404, "Пользователь не найден")
    if x.id == u.id and (data.role not in (None, "admin") or data.blocked): raise HTTPException(400, "Нельзя понизить или заблокировать себя")
    if data.role is not None:
        if data.role not in ROLES: raise HTTPException(400, "Неизвестная роль")
        x.role = data.role
    if data.school is not None: x.school = data.school.strip()[:120]
    if data.class_name is not None: x.class_name = data.class_name.strip()[:30]
    if data.blocked is not None:
        x.blocked = data.blocked
        if data.blocked: s.query(SessionToken).filter_by(user_id=x.id).delete()  # выкидываем из всех сессий
    audit(s, u.id, "admin_patch_user", f"user={uid} {data.model_dump(exclude_none=True)}"); s.commit()
    return user_dict(x)

@router.post("/admin/tasks")
def admin_add_task(data: TaskIn, u: User = Depends(require("teacher", "admin")), s: Session = Depends(db)):
    t = Task(prompt=clean(data.prompt, "Задание"), answer=clean(data.answer, "Ответ"), accepted=data.accepted.strip(),
             explanation=data.explanation.strip(), level=data.level, category=data.category)
    s.add(t); audit(s, u.id, "task_created", data.prompt[:80]); s.commit()
    return {"id": t.id}

@router.get("/admin/audit")
def admin_audit(u: User = Depends(require("admin")), s: Session = Depends(db)):
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "detail": a.detail, "at": a.created_at.isoformat()}
            for a in s.query(Audit).order_by(Audit.id.desc()).limit(200).all()]
