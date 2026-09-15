# -*- coding: utf-8 -*-
"""Ограничения переживают перевыпуск ключа.

И фильтры, и доступы внутри туннеля узел применяет по АДРЕСУ: он не знает ни
людей, ни ключей, ему известны только адреса пиров. Раскладку «адрес → правила»
считает бот и отдаёт её узлу.

Отсюда дыра, которая была: при перевыпуске человек получает новый адрес, а
раскладка на узле остаётся со старым. Правило есть, но оно про адрес, которым
уже никто не пользуется, — и перевыпуск ключа снимал и фильтры, и доступы.
Достаточно было нажать «перевыпустить» в своём же личном кабинете.

Поэтому после любого изменения состава пиров — выдали, перевыпустили, сняли —
раскладка пересчитывается и уезжает на узел заново. Дешёвая операция: считается
из базы, узлу отдаётся одним запросом.

Ошибку здесь не проглатываем молча, но и не роняем то, что её вызвало: человек
уже получил ключ, и падать после этого поздно. Пишем в журнал — владелец увидит
в аудите.
"""
from database import db


async def reapply(reason: str = ""):
    """Пересчитать и разложить ограничения заново. Возвращает (ок, что вышло)."""
    notes = []
    ok = True

    try:
        from filters import apply_filters
        good, msg = await apply_filters(reason)
        ok = ok and good
        notes.append(msg)
    except Exception as e:
        ok = False
        notes.append(f"фильтры: {e}")

    try:
        from acl import apply_access_rules
        good, msg = await apply_access_rules(reason)
        ok = ok and good
        notes.append(msg)
    except Exception as e:
        ok = False
        notes.append(f"доступы: {e}")

    if not ok:
        try:
            await db.log_event(
                "Ограничения",
                f"Не переприменились ({reason}): " + "; ".join(str(n) for n in notes))
        except Exception:
            pass
    return ok, "; ".join(str(n) for n in notes)
