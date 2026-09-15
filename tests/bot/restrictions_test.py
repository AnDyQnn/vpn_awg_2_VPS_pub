# -*- coding: utf-8 -*-
"""Ограничения пересобираются там, где меняется состав пиров.

Узел применяет и фильтры, и доступы по АДРЕСУ: людей и ключей он не знает.
Поэтому любое изменение состава — выдали, перевыпустили, сняли — делает
разложенную на узле картину устаревшей.

Чем это оборачивалось:
  • перевыпуск снимал фильтры и доступы: правило оставалось на адресе, которым
    уже никто не пользуется, а человек получал новый и чистый;
  • удаление оставляло правило на освободившемся адресе, и следующий хозяин
    получал чужие запреты, не понимая почему.

Здесь проверяется сам пересборщик: зовёт обе стороны, переживает их падение и
не роняет то, из-за чего его вызвали.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import restrictions                                # noqa: E402
import filters as F                                # noqa: E402
import acl                                         # noqa: E402

ok = True
called = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()

    async def fake_filters(reason=""):
        called.append(("фильтры", reason))
        return True, "фильтры разложены"

    async def fake_acl(reason=""):
        called.append(("доступы", reason))
        return True, "доступы разложены"

    F.apply_filters = fake_filters
    acl.apply_access_rules = fake_acl

    print("=== зовёт обе стороны ===")
    called.clear()
    good, msg = await restrictions.reapply("перевыпуск")
    check("получилось", good, msg)
    check("фильтры пересобраны", ("фильтры", "перевыпуск") in called, str(called))
    check("доступы тоже", ("доступы", "перевыпуск") in called,
          "роли и фильтры живут порознь, забыть одно — обычное дело")

    print()
    print("=== узел отказал по одной стороне ===")
    async def bad_filters(reason=""):
        return False, "узел недоступен"
    F.apply_filters = bad_filters

    called.clear()
    good, msg = await restrictions.reapply("проверка")
    check("сказано, что не получилось", not good, msg)
    check("вторая сторона всё равно разложена",
          ("доступы", "проверка") in called,
          "падение одной не повод бросать другую")
    check("причина названа", "недоступен" in msg, msg)

    print()
    print("=== одна из сторон упала с ошибкой ===")
    async def boom(reason=""):
        raise RuntimeError("что-то сломалось")
    F.apply_filters = boom

    called.clear()
    good, msg = await restrictions.reapply("падение")
    check("пересборщик не развалился", isinstance(msg, str))
    check("и об ошибке сказал", "сломалось" in msg, msg)
    check("доступы всё равно разложены", ("доступы", "падение") in called,
          "человек уже получил ключ — падать после этого поздно")

    events = await db.fetch_all(
        "SELECT message FROM events_log WHERE event_type='Ограничения' "
        "ORDER BY id DESC LIMIT 1")
    check("неудача попала в журнал", bool(events),
          "иначе владелец о ней не узнает никогда")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
