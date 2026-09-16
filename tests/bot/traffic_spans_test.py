# -*- coding: utf-8 -*-
"""Где проходит граница перевёрнутой истории трафика.

Сборщик когда-то писал отдачу в колонку приёма и наоборот: любой качающий
выглядел раздающим. Сам сборщик починен, но записанные до этого часы так и
лежат перевёрнутыми — их нужно поменять местами обратно.

Кнопки у этого нет и быть не должно: перевёрнутые данные просто неверны, и
выбирать тут нечего. Чинится само, один раз за всю жизнь установки.

Раз само — ошибиться нельзя ни разу. Опасность в том, что один час чьей-то
тяжёлой раздачи выглядит ТОЧНО так же, как ошибка сборщика. Поэтому ищем не
рубеж «всё до него перевёрнуто», а ПОЛОСЫ: ошибка сборщика длится часами
подряд, честная раздача — нет.

Рубеж, кстати, и не подошёл бы: на живых данных до 14 сентября приём и отдача
почти равны (колонки заполнялись одинаково, а не переставлялись), перевёрнут
ровно промежуток с 14-го по 15-е.

Проверяется это — и то, что второй раз ремонт не повторится.
"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from database import db                            # noqa: E402

ok = True
MB = 1024 * 1024


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def fill(rows):
    """rows: список (час, отдача_МБ, приём_МБ)."""
    await db.execute("DELETE FROM traffic_hourly WHERE user_uuid='tb-1'")
    for hour, up, down in rows:
        await db.execute(
            "INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out,"
            " packets_in, packets_out, peak_pps, samples)"
            " VALUES ('tb-1',$1,$2,$3,1,1,0,1)", hour, up * MB, down * MB)


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid='tb-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Границын','tb-1',TRUE)")
    base = datetime(2026, 9, 14, 0, 0)

    print("=== полоса перевёрнутых часов посреди верных ===")
    # Так выглядят живые данные: сначала ничего не разобрать, потом полоса
    # ошибки, потом всё правильно.
    rows = [(base + timedelta(hours=i), 500, 520) for i in range(24)]   # мутно
    rows += [(base + timedelta(hours=24 + i), 900, 60) for i in range(29)]  # ошибка
    rows += [(base + timedelta(hours=53 + i), 60, 900) for i in range(30)]  # верно
    await fill(rows)

    spans = await db.find_inverted_spans()
    check("нашлась одна полоса", len(spans) == 1, str(spans))
    check("начало верное", spans and spans[0][0] == base + timedelta(hours=24),
          str(spans[0][0]) if spans else "-")
    check("конец верный", spans and spans[0][1] == base + timedelta(hours=53),
          str(spans[0][1]) if spans else "-")
    n = await db.count_hourly_range(*spans[0])
    check("под разворот идут только они", n == 29, "строк: %d" % n)

    print()
    print("=== разворот чинит полосу и не трогает соседей ===")
    before_quiet = await db.fetch_val(
        "SELECT bytes_in FROM traffic_hourly WHERE user_uuid='tb-1' AND hour=$1",
        base)
    await db.swap_hourly_range(*spans[0])
    bad = await db.fetch_val(
        "SELECT COUNT(*) FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND hour >= $1 AND hour < $2 AND bytes_in > bytes_out", *spans[0])
    check("в полосе перевёрнутых не осталось", bad == 0, "осталось: %s" % bad)
    after_quiet = await db.fetch_val(
        "SELECT bytes_in FROM traffic_hourly WHERE user_uuid='tb-1' AND hour=$1",
        base)
    check("мутный участок не тронут", before_quiet == after_quiet,
          "до %s, после %s" % (before_quiet, after_quiet))
    late = await db.fetch_val(
        "SELECT bytes_out FROM traffic_hourly WHERE user_uuid='tb-1' AND hour=$1",
        base + timedelta(hours=53))
    check("верный час остался верным", late == 900 * MB)

    print()
    print("=== один час тяжёлой раздачи — не полоса ===")
    rows = [(base + timedelta(hours=i), 60, 900) for i in range(60)]
    rows[45] = (base + timedelta(hours=45), 900, 60)
    await fill(rows)
    check("полос нет", await db.find_inverted_spans() == [],
          "иначе честная раздача считалась бы ошибкой")

    print()
    print("=== тихие часы полосу не разрывают ===")
    # Ночью живого трафика нет — такие часы просто не в счёт, и полоса
    # ошибки не должна из-за них распадаться на куски.
    rows = [(base + timedelta(hours=i), 900, 60) for i in range(14)]
    rows[7] = (base + timedelta(hours=7), 2, 1)
    rows += [(base + timedelta(hours=14 + i), 60, 900) for i in range(20)]
    await fill(rows)
    spans = await db.find_inverted_spans()
    check("полоса одна, а не две", len(spans) == 1, str(spans))

    print()
    print("=== сборщик сломан прямо сейчас — не чиним следы ===")
    # Свежая полоса дотянулась до последнего часа: чинить надо сборщик, а
    # разворот только запутает картину.
    rows = [(base + timedelta(hours=i), 60, 900) for i in range(20)]
    rows += [(base + timedelta(hours=20 + i), 900, 60) for i in range(20)]
    await fill(rows)
    check("полос нет", await db.find_inverted_spans() == [],
          "хвост намеренно не закрываем")

    print()
    print("=== чинить нечего ===")
    await fill([(base + timedelta(hours=i), 60, 900) for i in range(30)])
    check("полос нет", await db.find_inverted_spans() == [],
          "у свежей установки сборщик исправен с первого дня")

    print()
    print("=== ремонт идёт сам и только один раз ===")
    import monitor
    await db.execute("DELETE FROM settings WHERE key='traffic_direction_repaired'")
    rows = [(base + timedelta(hours=i), 900, 60) for i in range(30)]
    rows += [(base + timedelta(hours=30 + i), 60, 900) for i in range(30)]
    await fill(rows)
    n = await monitor.repair_traffic_directions()
    check("починил при старте", n == 30, "строк: %s" % n)
    bad = await db.fetch_val(
        "SELECT COUNT(*) FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND bytes_in > bytes_out")
    check("перевёрнутых не осталось", bad == 0, "осталось: %s" % bad)
    check("отметка поставлена",
          bool(await db.get_setting("traffic_direction_repaired")))

    await fill(rows)          # снова «сломанные» данные
    n2 = await monitor.repair_traffic_directions()
    check("второй раз не чинит", n2 == 0, "строк: %s" % n2)
    still = await db.fetch_val(
        "SELECT COUNT(*) FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND bytes_in > bytes_out")
    check("данные не тронуты", still == 30, "перевёрнутых: %s" % still)

    await db.execute("DELETE FROM settings WHERE key='traffic_direction_repaired'")
    await db.execute("DELETE FROM traffic_hourly WHERE user_uuid='tb-1'")
    await db.execute("DELETE FROM users WHERE uuid='tb-1'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
