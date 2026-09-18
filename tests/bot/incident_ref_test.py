# -*- coding: utf-8 -*-
"""Номер инцидента виден в списке, и разобранные не копятся вечно.

Владелец: «в инцидентах нигде не указан его номер, кроме как на вебке бане».

Номер до базы доезжал исправно: узел считает его из самой попытки, кладёт в
журнал, бот забирает и пишет в свой столбец `ref` — в базе он есть у каждой
записи. А в список не попадал: выборка перечисляет столбцы поимённо, и `ref`
в этом перечне забыли. Экран честно рисовал `row.get("ref")`, получал `None` и
молчал — поломка, которую видно только глазами, и только если знать, что номер
там должен быть.

Смысл номера в том и был: человек приносит его со страницы отказа, а владелец
находит по нему событие. Поиск по номеру работал, а вот узнать событие в
списке — нет.

Второе: карточки не убирались никогда. Места они занимают мало, но список, где
всё за всё время, перестают открывать. Разобранные живут месяц, неразобранные —
квартал: то, до чего руки не дошли, уборка прятать не должна.
"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'ref-test%'")

    now = datetime.utcnow()
    await db.add_filter_hit(now, None, "Петя", "10.13.13.77", "1.2.3.4",
                            "ref-test.example", "порно", "D005-069F")

    print("=== номер в списке ===")
    rows = await db.list_filter_hits(limit=50)
    mine = [r for r in rows if r["domain"] == "ref-test.example"]
    check("запись нашлась", len(mine) == 1, "нашлось %d" % len(mine))
    check("номер отдан вместе со списком",
          bool(mine and mine[0].get("ref")),
          "экран рисует row.get('ref') — без столбца там всегда пусто")
    check("номер тот самый", bool(mine) and mine[0].get("ref") == "D005-069F",
          str(mine[0].get("ref")) if mine else "-")

    print()
    print("=== поиск по номеру человека ===")
    # Человек перепишет номер как получится: другим регистром, без дефиса.
    for typed in ("D005-069F", "d005069f", " d005-069F "):
        found = await db.find_filter_hit(typed)
        if not (found and found["domain"] == "ref-test.example"):
            check("номер набран как %r" % typed, False, "не нашёлся")
            break
    else:
        check("номер находится в любом написании", True,
              "регистр и дефис не важны")

    print()
    print("=== сроки хранения ===")
    check("разобранные живут не вечно",
          0 < db.HITS_KEEP_SEEN_DAYS <= 60,
          "сейчас %d дней" % db.HITS_KEEP_SEEN_DAYS)
    check("неразобранные живут дольше разобранных",
          db.HITS_KEEP_NEW_DAYS > db.HITS_KEEP_SEEN_DAYS,
          "иначе уборка прячет то, до чего руки не дошли")

    old_seen = now - timedelta(days=db.HITS_KEEP_SEEN_DAYS + 1)
    old_new = now - timedelta(days=db.HITS_KEEP_NEW_DAYS + 1)
    mid = now - timedelta(days=db.HITS_KEEP_SEEN_DAYS + 1)
    await db.add_filter_hit(old_seen, None, "Старый", "10.13.13.78", None,
                            "ref-test-seen.example", "порно", "AAAA-1111")
    await db.add_filter_hit(old_new, None, "Древний", "10.13.13.79", None,
                            "ref-test-oldnew.example", "порно", "BBBB-2222")
    await db.add_filter_hit(mid, None, "Просроченный", "10.13.13.80", None,
                            "ref-test-freshnew.example", "порно", "CCCC-3333")
    # Разобранной считается запись, которую открывали: помечаем одну.
    seen_row = await db.find_filter_hit("AAAA-1111")
    await db.mark_filter_hit_seen(seen_row["id"])

    gone = await db.cleanup_filter_hits()
    check("уборка что-то убрала", gone >= 2, "убрано %d" % gone)

    left = {r["domain"] for r in await db.list_filter_hits(limit=100)}
    check("свежая запись на месте", "ref-test.example" in left)
    check("разобранная старше срока убрана",
          "ref-test-seen.example" not in left,
          "месяц прошёл, разбор состоялся")
    check("неразобранная того же возраста осталась",
          "ref-test-freshnew.example" in left,
          "её ещё не смотрели — прятать нельзя")
    check("неразобранная старше квартала убрана",
          "ref-test-oldnew.example" not in left)

    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'ref-test%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
