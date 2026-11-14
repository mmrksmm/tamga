"""Отбраковка плохих строк корпуса.

В разговорниках встречаются обрывки словарных статей («(вечернем, заочном) отделении»),
а в самом датасете авторы предупреждают: выравнивание троек не проверялось построчно —
сбой вёрстки на странице мог сдвинуть колонки, и тогда к башкирской фразе прикреплён чужой перевод.
Такие пары до учеников доходить не должны, поэтому они отсеиваются при импорте и чистке базы.
"""
import re

WORD = re.compile(r"[^\s]+")
OPEN = "([{«"
CLOSE = ")]}»"

def words(t): return WORD.findall(t)

def not_bashkir(t):
    """Текст не на башкирской кириллице (например, расшифровка латиницей) — такому
    в заданиях не место: ученик решит, что так и пишут по-башкирски."""
    lat = sum(c.isalpha() and c.isascii() for c in t)
    cyr = sum(c.isalpha() and not c.isascii() for c in t)
    return lat > cyr and lat >= 3


def bad_pair(ba, ru):
    """Возвращает причину, по которой пару нельзя показывать, или пустую строку."""
    ba, ru = " ".join(ba.split()), " ".join(ru.split())
    if len(ba) < 3 or len(ru) < 2: return "слишком короткая"
    if not_bashkir(ba): return "башкирский текст записан латиницей"
    for t in (ba, ru):
        if t[0] in OPEN or t[0] in CLOSE or t[0] in ",.;:-–—/\\": return "начинается со скобки или знака"
        if t[-1] in ",;:/\\-–—" or t.endswith("..."): return "обрывок фразы"
        if sum(t.count(c) for c in OPEN) != sum(t.count(c) for c in CLOSE): return "непарные скобки"
        if re.search(r"\d\s*[).]\s*$", t): return "номер пункта"
    if ("?" in ba) != ("?" in ru): return "вопрос есть только с одной стороны"
    nb, nr = len(words(ba)), len(words(ru))
    if max(nb, nr) >= 4 and max(nb, nr) / max(1, min(nb, nr)) >= 2.5: return "длины не сходятся"
    letters = lambda t: sum(c.isalpha() for c in t)
    if letters(ba) < 3 or letters(ru) < 2: return "почти нет букв"
    return ""
