"""Модели базы данных (SQLAlchemy 2.0)."""
import os, datetime as dt
from typing import Optional
from sqlalchemy import create_engine, String, Integer, BigInteger, Text, ForeignKey, Boolean, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./tamga_v5.db")
if DB_URL.startswith("postgres://"): DB_URL = "postgresql+psycopg2://" + DB_URL[len("postgres://"):]   # формат хостингов
elif DB_URL.startswith("postgresql://"): DB_URL = "postgresql+psycopg2://" + DB_URL[len("postgresql://"):]
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def now():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

ROLES = ("student", "teacher", "moderator", "expert", "admin")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="student")
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    school: Mapped[str] = mapped_column(String(120), default="")
    class_name: Mapped[str] = mapped_column(String(30), default="")
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    school_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    letter: Mapped[str] = mapped_column(String(2), default="")
    pair: Mapped[str] = mapped_column(String(10), default="ba-ru")   # языковая пара, с которой работает пользователь
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class SessionToken(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # в базе только хеш токена
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(20), default="ru-ba")
    level: Mapped[str] = mapped_column(String(10), default="A1")
    category: Mapped[str] = mapped_column(String(60), default="Повседневное")
    answer: Mapped[str] = mapped_column(Text)
    accepted: Mapped[str] = mapped_column(Text, default="")  # доп. верные варианты, по одному в строке
    explanation: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    correct: Mapped[bool] = mapped_column(Boolean)
    day: Mapped[dt.date] = mapped_column(Date)

class Translation(Base):
    __tablename__ = "translations"
    id: Mapped[int] = mapped_column(primary_key=True)
    original: Mapped[str] = mapped_column(Text)
    proposed: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # pending -> review -> approved | rejected | archived
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    context: Mapped[str] = mapped_column(String(120), default="Общий")
    note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("translation_id", "user_id"),)  # один голос на человека — на уровне БД
    id: Mapped[int] = mapped_column(primary_key=True)
    translation_id: Mapped[int] = mapped_column(ForeignKey("translations.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    choice: Mapped[str] = mapped_column(String(20))

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class School(Base):
    __tablename__ = "schools"
    __table_args__ = (UniqueConstraint("city", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    translation_id: Mapped[int] = mapped_column(ForeignKey("translations.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class EmailCode(Base):  # ожидающая подтверждения регистрация
    __tablename__ = "email_codes"
    email: Mapped[str] = mapped_column(String(160), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(80))
    pw: Mapped[str] = mapped_column(String(256))
    school_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    letter: Mapped[str] = mapped_column(String(2), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)

class Fragment(Base):  # осмысленный фрагмент + координаты источника
    __tablename__ = "fragments"
    id: Mapped[int] = mapped_column(primary_key=True)
    text_ba: Mapped[str] = mapped_column(Text)
    source_doc: Mapped[str] = mapped_column(String(200), default="")
    chapter: Mapped[str] = mapped_column(String(120), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)       # номер абзаца/предложения
    audio_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # секунды (для аудио)
    audio_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class AutoTr(Base):  # автоперевод и заведомо ошибочный вариант для языковой пары
    __tablename__ = "auto_tr"
    __table_args__ = (UniqueConstraint("fragment_id", "pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"), index=True)
    pair: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(Text)
    wrong: Mapped[str] = mapped_column(Text, default="")

class Shown(Base):  # что именно показали пользователю (проверка на сервере)
    __tablename__ = "shown"
    __table_args__ = (UniqueConstraint("user_id", "fragment_id", "pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"))
    pair: Mapped[str] = mapped_column(String(10))
    shown_text: Mapped[str] = mapped_column(Text, default="")
    planted: Mapped[bool] = mapped_column(Boolean, default=False)

class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("user_id", "fragment_id", "pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"), index=True)
    pair: Mapped[str] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(10))   # confirm | correct
    text: Mapped[str] = mapped_column(Text, default="")  # голос за вариант ("" — голоса нет)
    planted: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[bool] = mapped_column(Boolean, default=False)   # поверил заведомой ошибке
    fixed: Mapped[bool] = mapped_column(Boolean, default=False)   # исправил заведомую ошибку
    xp: Mapped[int] = mapped_column(Integer, default=0)
    day: Mapped[dt.date] = mapped_column(Date, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class Consensus(Base):  # накопленная база подтверждённых переводов
    __tablename__ = "consensus"
    __table_args__ = (UniqueConstraint("fragment_id", "pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"), index=True)
    pair: Mapped[str] = mapped_column(String(10))
    translation: Mapped[str] = mapped_column(Text, default="")
    confirmed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="collecting")  # collecting | confirmed | expert_review
    expert: Mapped[bool] = mapped_column(Boolean, default=False)

class Media(Base):  # аудиофайл-источник: из него нарезаны фрагменты с отрезками по времени
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc: Mapped[str] = mapped_column(String(200), unique=True, index=True)   # совпадает с Fragment.source_doc
    filename: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(60), default="audio/mpeg")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class VoiceRec(Base):  # запись голоса к фрагменту: голосование учеников → эксперт → только потом звучит в заданиях
    __tablename__ = "voice_recs"
    id: Mapped[int] = mapped_column(primary_key=True)
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(12), default="voting", index=True)   # voting / expert / approved / rejected
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class VoiceVote(Base):
    __tablename__ = "voice_votes"
    __table_args__ = (UniqueConstraint("rec_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("voice_recs.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ok: Mapped[bool] = mapped_column(Boolean)

class FComment(Base):
    __tablename__ = "fcomments"
    id: Mapped[int] = mapped_column(primary_key=True)
    fragment_id: Mapped[int] = mapped_column(ForeignKey("fragments.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class TgUser(Base):  # пользователь Telegram-бота; состояние диалога (FSM) хранится в БД
    __tablename__ = "tg_users"
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(30), default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    pair: Mapped[str] = mapped_column(String(10), default="ba-ru")
    lang: Mapped[str] = mapped_column(String(2), default="ru")
    remind: Mapped[bool] = mapped_column(Boolean, default=True)
    last_remind: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    remind_tier: Mapped[int] = mapped_column(Integer, default=-1)   # последняя «ступень» напоминания, отправленная сегодня
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)

class OneTimeCode(Base):  # одноразовые коды: привязка Telegram к аккаунту и вход на сайт из бота
    __tablename__ = "one_time_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)

class ClassInvite(Base):  # код класса: учитель регистрирует учеников в свою школу и класс
    __tablename__ = "class_invites"
    code: Mapped[str] = mapped_column(String(12), primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    school_id: Mapped[int] = mapped_column(Integer)
    grade: Mapped[int] = mapped_column(Integer)
    letter: Mapped[str] = mapped_column(String(2), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# Простая миграция: дописывает колонки, появившиеся после создания базы (SQLite и PostgreSQL).
NEW_COLUMNS = {"users": {"pair": "VARCHAR(10) DEFAULT 'ba-ru'"},
               "tg_users": {"remind_tier": "INTEGER DEFAULT -1"}}

def ensure_columns():
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as c:
        for table, cols in NEW_COLUMNS.items():
            if not insp.has_table(table): continue
            have = {x["name"] for x in insp.get_columns(table)}
            for name, decl in cols.items():
                if name not in have: c.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {decl}"))
