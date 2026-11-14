"""Стартовые данные. Демо-аккаунты создаются только при DEMO_SEED=1 (по умолчанию включено)."""
import os, datetime as dt
from models import SessionLocal, User, Task, Translation, School, Fragment, AutoTr
from security import hash_pw

def seed():
    s = SessionLocal()
    try:
        if os.getenv("DEMO_SEED", "1") == "1" and not s.query(User).first():
            s.add_all([
                User(name="Алина", email="student@demo.ru", password=hash_pw("demo123"), role="student", xp=680, streak=7, last_active=dt.date.today() - dt.timedelta(days=1), school="Лицей №1", class_name="9А"),
                User(name="Учитель", email="teacher@demo.ru", password=hash_pw("demo123"), role="teacher", school="Лицей №1", class_name="9А"),
                User(name="Модератор", email="moderator@demo.ru", password=hash_pw("demo123"), role="moderator"),
                User(name="Эксперт", email="expert@demo.ru", password=hash_pw("demo123"), role="expert"),
                User(name="Администратор", email="admin@demo.ru", password=hash_pw("demo123"), role="admin"),
            ])
            s.flush()
            s.add_all([
                Task(prompt="Доброе утро", answer="Хәйерле иртә", level="A1", category="Приветствия", explanation="Устойчивое приветствие, употребляемое в первой половине дня."),
                Task(prompt="Я люблю читать книги", answer="Мин китап уҡырға яратам", level="A2", explanation="Конструкция с глаголом яратам."),
                Task(prompt="Сегодня хорошая погода", answer="Бөгөн һауа торошо яҡшы", level="A2", category="Природа", explanation="Бөгөн — сегодня; һауа торошо — погода."),
                Translation(original="Доброе утро", proposed="Хәйерле иртә", author_id=1, status="approved", context="Приветствия", note="Демонстрационная запись"),
                Translation(original="Спасибо большое", proposed="Ҙур рәхмәт", author_id=1, status="pending", context="Общение"),
                Translation(original="Как дела?", proposed="Хәлдәр нисек?", author_id=1, status="review", context="Общение"),
            ])
            s.commit()
        if not s.query(School).first(): seed_schools(s)
        if not s.query(Fragment).first(): seed_fragments(s)
        s.query(Fragment).filter(Fragment.source_doc.like("Демо-корпус%")).update({"source_doc": DOC}, synchronize_session=False); s.commit()
        # первый админ для боевого запуска: ADMIN_EMAIL и ADMIN_PASSWORD в переменных окружения
        em, pw = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
        if em and pw and not s.query(User).filter_by(role="admin").first():
            s.add(User(name="Администратор", email=em.lower(), password=hash_pw(pw), role="admin")); s.commit()
    finally:
        s.close()


CITIES = "Агидель Кумертау Межгорье Нефтекамск Октябрьский Салават Сибай Стерлитамак Уфа".split()
DISTRICTS = ("Абзелиловский Альшеевский Архангельский Аскинский Аургазинский Баймакский Бакалинский Балтачевский Белебеевский Белокатайский Белорецкий Бирский "
 "Благоварский Благовещенский Буздякский Бураевский Бурзянский Гафурийский Давлекановский Дуванский Дюртюлинский Зианчуринский Зилаирский Иглинский Илишевский "
 "Ишимбайский Караидельский Кармаскалинский Кигинский Краснокамский Кугарчинский Кушнаренковский Куюргазинский Мелеузовский Мечетлинский Мишкинский Салаватский "
 "Стерлитамакский Туймазинский Уфимский Учалинский Хайбуллинский Чекмагушевский Чишминский Шаранский Янаульский").split()
# Реальные школы, которые были видны на shkola.city/ba (первые 10 для Уфы и Сибая). Полный список: python import_schools.py
UFA = ["Гармония", "Средняя общеобразовательная школа № 88", "Школа № 18", "Средняя общеобразовательная школа № 87", "Study_Я", "Частная школа № 1", "Школа № 97", "Татарская воскресная школа № 2", "Поколение", "Школа № 98"]
SIBAY = ["Средняя общеобразовательная школа № 6", "Средняя общеобразовательная школа № 11", "Гимназия", "Сибайская коррекционная школа", "Средняя общеобразовательная школа № 8", "Средняя Общеобразовательная Школа № 10", "Средняя общеобразовательная школа № 5", "Средняя общеобразовательная школа № 1", "Средняя общеобразовательная школа № 7", "Средняя Общеобразовательная Школа № 14"]
NONE = "— моей школы пока нет в списке —"

def seed_schools(s):
    for c in CITIES: s.add(School(city=c, name=NONE))
    for d in DISTRICTS: s.add(School(city=d + " район", name=NONE))
    for n in UFA: s.add(School(city="Уфа", name=n))
    for n in SIBAY: s.add(School(city="Сибай", name=n))
    s.commit()

DOC = "Учебный корпус Тамги"
FR = [  # башкирский, русский, заведомо неверный русский, английский, неверный английский
 ("Мин бөгөн китап уҡыйым.", "Я сегодня читаю книгу.", "Я вчера читал книгу.", "I am reading a book today.", "I read a newspaper yesterday."),
 ("Беҙ мәктәпкә барабыҙ.", "Мы идём в школу.", "Мы идём домой.", "We are going to school.", "We are going home."),
 ("Әсәйем өйҙә.", "Моя мама дома.", "Моя сестра дома.", "My mother is at home.", "My sister is at home."),
 ("Бөгөн һауа торошо яҡшы.", "Сегодня хорошая погода.", "Сегодня плохая погода.", "The weather is nice today.", "The weather is bad today."),
 ("Мин сәй эсәм.", "Я пью чай.", "Я пью молоко.", "I am drinking tea.", "I am drinking milk."),
 ("Ул Өфөлә йәшәй.", "Он живёт в Уфе.", "Он едет в Уфу.", "He lives in Ufa.", "He is going to Ufa."),
 ("Ағиҙел — матур йылға.", "Агидель — красивая река.", "Агидель — большое озеро.", None, None),
 ("Йәй эҫе була.", "Лето бывает жарким.", "Лето бывает холодным.", None, None),
 ("Китап өҫтәлдә.", "Книга на столе.", "Книга в сумке.", None, None),
 ("Балалар урамда уйнай.", "Дети играют на улице.", "Дети спят дома.", None, None),
 ("Беҙ башҡортса һөйләшәбеҙ.", "Мы говорим по-башкирски.", "Мы говорим по-русски.", None, None),
 ("Ҡыш ҡар яуа.", "Зимой идёт снег.", "Зимой идёт дождь.", None, None),
 ("Мин дуҫымды көтәм.", "Я жду друга.", "Я вижу друга.", None, None),
 ("Олатайым ауылда йәшәй.", "Мой дедушка живёт в деревне.", "Мой дедушка живёт в городе.", None, None),
 ("Бесәй һыу эсә.", "Кошка пьёт воду.", "Кошка ест мясо.", None, None),
 ("Ул яңы китап һатып алды.", "Он купил новую книгу.", "Он продал старую книгу.", None, None),
 ("Ҡорт бал бирә.", "Пчела даёт мёд.", "Пчела даёт молоко.", None, None),
 ("Урман һалҡын һәм тымыҡ.", "Лес прохладный и тихий.", "Лес жаркий и шумный.", None, None),
]
def seed_fragments(s):
    for i, (ba, ru, ru_w, en, en_w) in enumerate(FR, 1):
        f = Fragment(text_ba=ba, source_doc=DOC, chapter="Раздел 1", position=i); s.add(f); s.flush()
        s.add(AutoTr(fragment_id=f.id, pair="ba-ru", text=ru, wrong=ru_w))
        if en: s.add(AutoTr(fragment_id=f.id, pair="ba-en", text=en, wrong=en_w))
    s.add(Fragment(text_ba="Һаумыһығыҙ, ҡәҙерле дуҫтар!", source_doc=DOC, chapter="Раздел 1", position=len(FR) + 1))  # без автоперевода — перевод «с нуля»
    s.commit()
