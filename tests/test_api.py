import os, sys, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db")
os.environ.update(DEV_SHOW_CODE="1", DEMO_SEED="1", CONSENSUS_MIN_VOTERS="3", AUDIO_DIR=tempfile.mkdtemp(), TTS_DISABLED="1", PLANT_RATE="0")
os.environ.pop("SMTP_HOST", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from fastapi.testclient import TestClient
from main import app
from models import SessionLocal, Answer, Consensus, Fragment, User
import extra
c = TestClient(app)

def login(email, pw="demo123"):
    r = c.post("/api/login", json={"email": email, "password": pw})
    return {"Authorization": "Bearer " + r.json()["token"]}

def register(email):
    d = c.post("/api/register/start", json={"name": "Тест", "email": email, "password": "12345678"}).json()
    r = c.post("/api/register/confirm", json={"email": email, "code": d["dev_code"]}).json()
    assert r["user"]["role"] == "student"
    return {"Authorization": "Bearer " + r["token"]}

def test_goal_counts_only_correct():
    """Ловушка не засчитывается: после неё до огонька остаётся ещё одно задание."""
    import extra
    h = register("trap@test.ru")
    old = extra.PLANT_RATE
    try:
        extra.PLANT_RATE = 1.0                      # все задания — с подставной ошибкой
        it = c.get("/api/daily?pair=ba-ru", headers=h).json()["items"][0]
        r = c.post("/api/answer", json={"fragment_id": it["id"], "pair": "ba-ru", "kind": "confirm"}, headers=h).json()
        assert r["error"] and r["today"] == 0 and r["user"]["streak"] == 0
    finally:
        extra.PLANT_RATE = old
    assert len(c.get("/api/daily?pair=ba-ru", headers=h).json()["items"]) == 5   # норма не уменьшилась

def test_daily_goal_streak_and_extra():
    h = register("streak@test.ru")
    d = c.get("/api/daily?pair=ba-ru", headers=h).json()
    assert len(d["items"]) == 5
    for i, it in enumerate(d["items"]):
        kind = "confirm" if it["mode"] == "check" else "correct"
        r = c.post("/api/answer", json={"fragment_id": it["id"], "pair": "ba-ru", "kind": kind, "text": "вариант"}, headers=h).json()
        assert (r["user"]["streak"] == 1) == (i == 4)        # огонёк — только на пятом переводе
    assert c.get("/api/daily?pair=ba-ru", headers=h).json()["items"] == []
    assert len(c.get("/api/daily?pair=ba-ru&extra=true", headers=h).json()["items"]) == 10   # сверх нормы — порциями

def test_consensus_by_share():
    s = SessionLocal(); f = s.query(Fragment).first(); uid = s.query(User).first().id
    def put(texts):
        s.query(Answer).filter_by(fragment_id=f.id, pair="ba-zh").delete()
        for i, t in enumerate(texts):
            s.add(Answer(user_id=uid + i, fragment_id=f.id, pair="ba-zh", kind="correct", text=t, day=extra.dt.date.today()))
        s.flush(); return extra.recompute(s, f.id, "ba-zh").status
    assert put(["A", "A"]) == "collecting"                       # меньше 3 ответов
    assert put(["A"] * 8 + ["B"]) == "confirmed"                 # B = 11% < 20% — шум
    assert put(["A"] * 6 + ["B"] * 4) == "confirmed"             # 60% — подтверждён
    assert put(["A"] * 5 + ["B"] * 5) == "expert_review"         # два сильных варианта
    assert put(["A"] * 5 + ["B", "C", "D", "E", "F"]) == "confirmed"  # остальные по 10% — шум
    s.rollback(); s.close()

def test_roles_and_api_key():
    assert c.get("/api/v1/export").status_code == 401
    assert c.get("/api/v1/export", headers=login("student@demo.ru")).status_code == 403
    assert c.get("/api/v1/export", headers=login("admin@demo.ru")).status_code == 200

def test_config():
    cfg = c.get("/api/config").json()
    assert cfg["goal"] == 5 and cfg["noise"] == 20

def test_teacher_invite_and_csv():
    h = login("teacher@demo.ru")
    sid = c.get("/api/schools?city=Уфа").json()[1]["id"]
    c.patch("/api/me/school", json={"school_id": sid, "grade": 5, "letter": "В"}, headers=h)
    code = c.post("/api/teacher/invite", headers=h).json()["code"]
    d = c.post("/api/register/start", json={"name": "Ученик", "email": "kid@test.ru", "password": "12345678", "class_code": code}).json()
    r = c.post("/api/register/confirm", json={"email": "kid@test.ru", "code": d["dev_code"]}).json()
    assert r["user"]["class_name"] == "5В"
    csv_ = c.get("/api/teacher/report?format=csv", headers=h)
    assert csv_.status_code == 200 and "Ученик" in csv_.text
    assert c.post("/api/register/start", json={"name": "X", "email": "x@test.ru", "password": "12345678", "class_code": "WRONG1"}).status_code == 400

def test_learn():
    h = login("student@demo.ru")
    assert len(c.get("/api/learn/facts", headers=h).json()["facts"]) >= 10
    q = c.get("/api/learn/quiz", headers=h).json()[0]
    assert "right" not in q
    r = c.post("/api/learn/quiz/check", json={"id": q["id"], "choice": 0}, headers=h).json()
    assert "explain" in r
    b = c.get("/api/learn/build", headers=h).json()
    assert len(b["tiles"]) > b["count"]                      # есть лишние слова
    ans = c.post("/api/learn/build/check", json={"id": b["id"], "words": ["x"]}, headers=h).json()
    right = ans["answer"].rstrip(".!?").replace("—", " ").split()
    assert c.post("/api/learn/build/check", json={"id": b["id"], "words": [w for w in right if w]}, headers=h).json()["correct"]
    assert len(c.get("/api/learn/test", headers=h).json()) == 10

def test_voice_recording():
    h = login("expert@demo.ru")
    assert c.get("/api/audio/1").status_code == 404
    assert c.post("/api/fragments/1/audio", content=b"x" * 5000, headers=h).json()["status"] == "voting"
    assert c.get("/api/audio/1").status_code == 404           # до голосования и эксперта запись не звучит
    assert c.post("/api/fragments/1/audio", content=b"x" * 5000, headers=login("student@demo.ru")).status_code == 403

def test_report_hides_bad_task():
    from quality import bad_pair
    assert bad_pair("Мин һеҙҙе сәғәт етелә көтәм", "(вечернем, заочном) отделении")   # обрывок словарной статьи
    assert bad_pair("Һеҙҙең хәлдәрегеҙ нисек?", "Все хорошо")                         # сбитое выравнивание
    assert not bad_pair("Мин бөгөн китап уҡыйым.", "Я сегодня читаю книгу.")
    h = login("student@demo.ru")
    fid = c.get("/api/daily?pair=ba-ru", headers=h).json()["items"][0]["id"]
    r = c.post(f"/api/fragments/{fid}/report", headers=h).json()
    assert r["reports"] == 1 and not r["hidden"]                                      # ученику нужно подтверждение
    assert c.post(f"/api/fragments/{fid}/report", headers=h).status_code == 409        # повторно нельзя
    assert c.post(f"/api/fragments/{fid}/report", headers=login("expert@demo.ru")).json()["hidden"]
    assert all(x["id"] != fid for x in c.get("/api/daily?pair=ba-ru&extra=true", headers=h).json()["items"])

def test_stats_extras():
    h = login("student@demo.ru")
    d = c.get("/api/me/stats", headers=h).json()
    assert len(d["days"]) == 28 and d["days"][-1]["d"] == str(__import__("datetime").date.today())
    assert d["best_streak"] >= d["streak"] and "xp_translate" in d and "since" in d

def test_pair_in_profile():
    """Языковая пара хранится в профиле, а не в браузере: после перезахода она та же."""
    h = register("pair@test.ru")
    assert c.get("/api/me", headers=h).json()["pair"] == "ba-ru"
    assert c.patch("/api/me/pair", json={"pair": "ba-kk"}, headers=h).json()["pair"] == "ba-kk"
    assert c.patch("/api/me/pair", json={"pair": "ba-xx"}, headers=h).status_code == 400
    assert c.get("/api/me", headers=login("pair@test.ru", "12345678")).json()["pair"] == "ba-kk"

def test_consensus_counts_synonyms_together():
    """Один и тот же перевод разными словами — это один вариант; подставная ошибка — другой."""
    assert extra.same_meaning(extra.canon("Я сегодня читаю книгу."), extra.canon("Сегодня я читаю книгу"))
    assert extra.same_meaning(extra.canon("Моя мама дома"), extra.canon("Моя мать дома"))
    assert extra.same_meaning(extra.canon("Я читаю книгу"), extra.canon("я читаю книжку"))
    assert not extra.same_meaning(extra.canon("Я сегодня читал книгу"), extra.canon("Я вчера читал книгу"))
    assert not extra.same_meaning(extra.canon("Сегодня хорошая погода"), extra.canon("Сегодня плохая погода"))

    s = SessionLocal()
    fid = s.query(Fragment).first().id
    s.query(Answer).filter_by(fragment_id=fid, pair="ba-ru").delete()
    s.query(Consensus).filter_by(fragment_id=fid, pair="ba-ru").delete(); s.commit()
    for i, txt in enumerate(["Моя мама дома.", "моя мать дома", "Дома моя мама", "Моя сестра дома"]):
        u = User(name=f"С{i}", email=f"syn{i}@t.ru", password="x", role="student")
        s.add(u); s.flush()
        s.add(Answer(user_id=u.id, fragment_id=fid, pair="ba-ru", kind="correct", text=txt, day=__import__("datetime").date.today()))
    s.commit()
    (top, *rest), total = extra.tally(s, fid, "ba-ru")
    assert total == 4 and top[1] == 3 and len(rest) == 1           # три формулировки слились в один вариант
    assert extra.recompute(s, fid, "ba-ru").status == "confirmed"   # 3 из 4 — это 75 %
    s.close()

def test_audio_source_slice_and_play():
    """Аудиоисточник: файл + расшифровка с отметками времени → фрагменты с отрезками."""
    h, doc = login("admin@demo.ru"), "Радиопередача «Иртә»"
    assert c.post("/api/admin/slice", json={"text": "00:00 Хәйерле иртә.", "source_doc": doc, "mode": "audio"}, headers=h).status_code == 400
    assert c.post(f"/api/admin/audio?doc={doc}", content=b"ID3" + b"x" * 5000,
                  headers={**h, "Content-Type": "audio/mpeg"}).json()["ok"]
    r = c.post("/api/admin/slice", json={"text": "00:00 Хәйерле иртә, тыңлаусылар.\n0:07 Бөгөн һауа торошо яҡшы.\n[1:02:03] Һаубулығыҙ.",
                                         "source_doc": doc, "chapter": "Выпуск 1", "mode": "audio"}, headers=h).json()
    assert r["fragments"] == 3
    s = SessionLocal()
    f = s.query(Fragment).filter_by(source_doc=doc).order_by(Fragment.position).first()
    assert (f.audio_from, f.audio_to) == (0, 7)
    s.close()
    assert c.get(f"/api/media/{f.id}").content.startswith(b"ID3")
    assert c.get("/api/v1/fragments", headers=h).json()[0]["media"] in (True, False)
    assert c.post(f"/api/admin/audio?doc={doc}", content=b"x" * 5000,
                  headers={**login("student@demo.ru"), "Content-Type": "audio/mpeg"}).status_code == 403

def test_audio_auto_markup():
    """Автоматическая разметка: текст учителя раскладывается по паузам записи."""
    import asr, wave, struct, math, io
    h, doc = login("admin@demo.ru"), "Запись для разметки"
    buf = io.BytesIO()
    with wave.open(buf, "w") as w:                       # три звучащих куска с паузами между ними
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        tone = [int(9000 * math.sin(i * 0.2)) for i in range(16000)]
        sil = [0] * 32000
        w.writeframes(b"".join(struct.pack("<h", v) for v in (tone + sil) * 3))
    assert c.post(f"/api/admin/audio?doc={doc}", content=buf.getvalue(),
                  headers={**h, "Content-Type": "audio/wav"}).json()["ok"]
    body = {"doc": doc, "mode": "pauses", "text": "Беренсе һөйләм. Икенсе һөйләм. Өсөнсө һөйләм."}
    if not asr.can_pauses():   # режим «по паузам» не требует модели — только чтение аудио (av + numpy)
        assert c.post("/api/admin/transcribe", json=body, headers=h).status_code == 503
        return
    import time
    jid = c.post("/api/admin/transcribe", json=body, headers=h).json()["job"]
    for _ in range(100):                                   # разметка идёт в фоне
        st = c.get(f"/api/admin/transcribe/{jid}", headers=h).json()
        if st["state"] != "run": break
        time.sleep(0.2)
    assert st["state"] == "done", st.get("error")
    assert st["lines"] == 3 and st["text"].startswith("00:00 Беренсе")
    assert c.post("/api/admin/slice", json={"text": st["text"], "source_doc": doc, "mode": "audio"}, headers=h).json()["fragments"] == 3
    assert c.get("/api/admin/transcribe/неттакого", headers=h).status_code == 404
    assert c.get("/api/admin/asr-check", headers=h).json()["ok"] in (True, False)
    assert c.post("/api/admin/transcribe", json={**body, "doc": "Нет такого"}, headers=h).status_code == 404
    assert c.post("/api/admin/transcribe", json=body, headers=login("student@demo.ru")).status_code == 403

def test_xp_only_after_confirmation():
    """Очки за перевод начисляются, когда вариант подтверждён другими, а не за отправку."""
    s = SessionLocal()
    fid = s.query(Fragment).first().id
    s.query(Answer).filter_by(fragment_id=fid, pair="ba-ru").delete()
    s.query(Consensus).filter_by(fragment_id=fid, pair="ba-ru").delete(); s.commit()
    us = []
    for i in range(3):
        u = User(name=f"Х{i}", email=f"xp{i}@t.ru", password="x", role="student", xp=0)
        s.add(u); s.flush(); us.append(u.id)
        s.add(Answer(user_id=u.id, fragment_id=fid, pair="ba-ru", kind="correct",
                     text="Здравствуйте, друзья." if i else "Здравствуйте друзья",
                     day=__import__("datetime").date.today()))
        s.flush()
        c_ = extra.recompute(s, fid, "ba-ru"); s.commit()
        if i < 2:
            assert c_.status == "collecting"
            assert all(s.get(User, x).xp == 0 for x in us)      # голосов мало — очков нет ни у кого
    assert c_.status == "confirmed"
    assert [s.get(User, x).xp for x in us] == [extra.XP_CONFIRMED] * 3   # подтвердилось — заплатили всем
    s.query(Answer).filter_by(fragment_id=fid, pair="ba-ru").delete()
    s.query(Consensus).filter_by(fragment_id=fid, pair="ba-ru").delete(); s.commit(); s.close()

def test_latin_never_reaches_students():
    """Расшифровка латиницей не попадает в задания, а уже попавшая прячется одной кнопкой."""
    h = login("admin@demo.ru")
    r = c.post("/api/admin/slice", json={
        "text": "Шулай итеп, Ибраһимдан Дауытҡа тиклем ун дүрт быуын. "
                "Dawtdan alip wavilanqa kuselgan wakat qatiklim undurt boon. "
                "Мәсих тыуғанға тиклем ун дүрт быуын булды.",
        "source_doc": "Проверка латиницы", "mode": "sentence"}, headers=h).json()
    assert r["fragments"] == 2 and r["skipped"] == 1
    assert c.post("/api/admin/slice", json={"text": "00:00 Dawtdan alip wavilanqa kuselgan.",
                                            "source_doc": "Только латиница", "mode": "audio"}, headers=h).status_code == 400
    s = SessionLocal()                                        # фрагмент из старой расшифровки
    s.add(Fragment(text_ba="Ibraheem hem daud tuqumunan bulgan.", source_doc="Старое", active=True)); s.commit(); s.close()
    assert c.post("/api/admin/cleanup", headers=h).json()["hidden"] >= 1
    s = SessionLocal()
    from quality import not_bashkir
    assert not any(not_bashkir(f.text_ba) for f in s.query(Fragment).filter_by(active=True))
    s.close()

def test_voice_recording_needs_votes_and_expert():
    """Запись голоса не звучит сразу: голосование учеников → эксперт → только потом в заданиях."""
    from models import VoiceRec, VoiceVote
    s = SessionLocal(); fid = s.query(Fragment).filter_by(active=True).first().id
    author = User(name="Учитель З", email="rec_t@t.ru", password="x", role="teacher"); s.add(author); s.flush()
    r = VoiceRec(fragment_id=fid, user_id=author.id, token="testtoken123"); s.add(r); s.flush()
    rid = r.id
    voters = []
    for i in range(3):
        u = User(name=f"Г{i}", email=f"rv{i}@t.ru", password="x", role="student"); s.add(u); s.flush(); voters.append(u.id)
    s.commit()
    extra.AUDIO.mkdir(parents=True, exist_ok=True)
    (extra.AUDIO / "rec_testtoken123.webm").write_bytes(b"x" * 2000)
    live = extra.AUDIO / f"{fid}.webm"
    if live.exists(): live.unlink()
    h = login("admin@demo.ru")
    assert c.post(f"/api/rec/{rid}/decide", json={"ok": True}, headers=h).status_code == 400   # эксперт не может раньше учеников
    for i, uid in enumerate(voters):
        s.add(VoiceVote(rec_id=rid, user_id=uid, ok=True)) if i < 2 else None
    s.commit(); s.close()
    assert c.post(f"/api/rec/{rid}/vote", json={"ok": True}, headers=h).json()["status"] == "expert"   # третий голос
    assert not live.exists()                                   # ученики одобрили, но запись ещё не звучит
    assert any(x["id"] == rid and x["status"] == "expert" for x in c.get("/api/expert/recs", headers=h).json())
    assert c.post(f"/api/rec/{rid}/decide", json={"ok": True}, headers=h).json()["status"] == "approved"
    assert live.exists()                                       # только теперь
    live.unlink()


def test_flame_xp_and_code_only_school():
    """За зажжённый огонёк — бонус XP; школу из списка выбирает только учитель/админ."""
    h = register("flame@test.ru")
    got = []
    for it in c.get("/api/daily?pair=ba-ru", headers=h).json()["items"]:
        kind = "confirm" if it["mode"] == "check" else "correct"
        r = c.post("/api/answer", json={"fragment_id": it["id"], "pair": "ba-ru", "kind": kind, "text": "вариант"}, headers=h).json()
        got.append(r["flame_xp"])
    assert got[:4] == [0, 0, 0, 0] and got[4] == extra.XP_FLAME       # бонус — ровно на пятом верном задании
    assert c.get("/api/me/stats", headers=h).json()["xp_flame"] == extra.XP_FLAME
    # ученик не может выбрать школу из списка — только по коду класса
    sid = c.get("/api/schools?city=Уфа").json()[1]["id"]
    assert c.patch("/api/me/school", json={"school_id": sid, "grade": 5, "letter": "А"}, headers=h).status_code == 403
    # регистрация не принимает школу напрямую: поле школы игнорируется, класс — только по коду
    d = c.post("/api/register/start", json={"name": "Б", "email": "b@test.ru", "password": "12345678", "school_id": sid}).json()
    r = c.post("/api/register/confirm", json={"email": "b@test.ru", "code": d["dev_code"]}).json()
    assert r["user"]["school"] == "" and r["user"]["class_name"] == ""


def test_streak_repair_and_levels():
    """Серию можно выкупить за XP при пропуске ровно одного дня; уровень виден в комментариях и отчёте класса."""
    h = register("repair@test.ru")
    s = SessionLocal(); u = s.query(User).filter_by(email="repair@test.ru").first()
    u.streak, u.last_active, u.xp = 7, extra.dt.date.today() - extra.dt.timedelta(days=2), 650
    s.commit()
    d = c.get("/api/me/stats", headers=h).json()
    assert d["streak"] == 0 and d["can_fix"] and d["lost_streak"] == 7 and d["fix_cost"] == extra.STREAK_REPAIR_XP
    r = c.post("/api/me/streak-fix", headers=h).json()
    assert r["streak"] == 7 and r["user"]["xp"] == 650 - extra.STREAK_REPAIR_XP
    assert c.post("/api/me/streak-fix", headers=h).status_code == 400       # второй раз подряд нельзя
    s.close()
    # уровень в комментариях
    fid = s.query(Fragment).first().id
    c.post(f"/api/fragments/{fid}/comments", json={"text": "Вопрос по переводу"}, headers=h)
    cm = c.get(f"/api/fragments/{fid}/comments", headers=h).json()[-1]
    assert cm["level"] == (650 - extra.STREAK_REPAIR_XP) // 500 + 1
    # уровень в отчёте учителя
    th = login("teacher@demo.ru")
    rep = c.get("/api/teacher/report", headers=th).json()
    assert all("level" in row for row in rep)
    assert "Уровень" in c.get("/api/teacher/report?format=csv", headers=th).text
