"""Пароли (Argon2id), сессии, роли, лимиты запросов, аудит."""
import os, hashlib, secrets, time, collections, datetime as dt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from models import SessionLocal, SessionToken, User, Audit, now

ph = PasswordHasher()  # Argon2id по умолчанию
DUMMY_HASH = ph.hash("dummy-password")
TOKEN_DAYS = 7

def hash_pw(p): return ph.hash(p)

def check_pw(h, p):
    try: return ph.verify(h, p)
    except (VerifyMismatchError, InvalidHashError): return False

def db():
    s = SessionLocal()
    try: yield s
    finally: s.close()

def _sha(t): return hashlib.sha256(t.encode()).hexdigest()

def new_token(s: Session, user: User) -> str:
    raw = secrets.token_urlsafe(36)
    s.add(SessionToken(token_hash=_sha(raw), user_id=user.id, expires_at=now() + dt.timedelta(days=TOKEN_DAYS)))
    s.commit()
    return raw

def drop_token(s: Session, raw: str):
    x = s.get(SessionToken, _sha(raw))
    if x: s.delete(x); s.commit()

def current_user(authorization: str | None = Header(default=None), s: Session = Depends(db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    sess = s.get(SessionToken, _sha(authorization[7:]))
    if not sess or sess.expires_at < now():
        raise HTTPException(401, "Сессия истекла, войдите заново")
    u = s.get(User, sess.user_id)
    if not u or u.blocked:
        raise HTTPException(403, "Аккаунт заблокирован")
    return u

def require(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role not in roles: raise HTTPException(403, "Недостаточно прав")
        return u
    return dep

class Limiter:
    """Скользящее окно в памяти процесса. Для нескольких воркеров нужен Redis."""
    def __init__(self): self.h = collections.defaultdict(collections.deque)
    def hit(self, key, limit, window):
        q, t = self.h[key], time.time()
        while q and q[0] < t - window: q.popleft()
        if len(q) >= limit: raise HTTPException(429, "Слишком много запросов, подождите немного")
        q.append(t)

limiter = Limiter()

TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"

def ip_of(request: Request) -> str:
    # за обратным прокси (Caddy, nginx, хостинг) реальный адрес приходит в X-Forwarded-For
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd: return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"

def audit(s: Session, user_id, action, detail=""):
    s.add(Audit(user_id=user_id, action=action, detail=detail[:500]))
