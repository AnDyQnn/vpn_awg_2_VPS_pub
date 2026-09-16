# -*- coding: utf-8 -*-
"""Где проходит граница перевёрнутой истории трафика.

Сборщик когда-то писал отдачу в колонку приёма и наоборот: любой качающий
выглядел раздающим. Сам сборщик починен, но записанные до этого часы так и
лежат перевёрнутыми — их нужно поменять местами обратно.

Кнопки у этого нет и быть не должно: перевёрнутые данные просто неверны, и
выбирать тут нечего. Чинится само, один раз за всю жизнь установки.

Раз само — ошибиться нельзя ни разу. Опасность в том, что один час чьей-то
тяжёлой раздачи выглядит ТОЧНО так же, как ошибка сборщика; приняв его за
границу, мы перевернули бы всю верную историю. Поэтому граница ищется не по
признаку, а по картине: длинная перевёрнутая полоса, длинная правильная, и
чистые края.

Проверяется ровно это — и то, что второй раз ремонт не повторится.
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
    flip = base + timedelta(hours=29)      # 15.09 05:00 — как было на живом

    print("=== история с переломом ===")
    rows = []
    for i in range(29):                     # перевёрнутые часы: отдача >> приём
        rows.append((base + timedelta(hours=i), 900, 60))
    for i in range(29, 50):                 # верные часы: приём >> отдача
        rows.append((base + timedelta(hours=i), 60, 900))
    await fill(rows)

    border = await db.find_direction_border()
    check("граница найдена", border is not None, str(border))
    check("и это именно час перелома", border == flip,
          "нашли %s, ждали %s" % (border, flip))

    n = await db.count_hourly_before(border)
    check("под разворот идут только перевёрнутые", n == 29, "строк: %d" % n)

    print()
    print("=== разворот чинит старое и не трогает новое ===")
    await db.swap_hourly_directions(border)
    bad = await db.fetch_val(
        "SELECT COUNT(*) FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND bytes_in > bytes_out")
    check("перевёрнутых не осталось", bad == 0, "осталось: %s" % bad)
    late = await db.fetch_val(
        "SELECT bytes_out FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND hour=$1", flip)
    check("верный час остался верным", late == 900 * MB,
          "приём: %s МБ" % (late // MB if late else 0))

    print()
    print("=== тихие часы не сбивают границу ===")
    # Ночью живого трафика нет, остаются служебные пакеты — они симметричны и
    # о направлении не говорят ничего. Судить по ним нельзя.
    rows = []
    for i in range(30):
        rows.append((base + timedelta(hours=i), 900, 60))       # перевёрнутые
    rows.append((base + timedelta(hours=30), 2, 1))             # тихий час
    for i in range(31, 60):
        rows.append((base + timedelta(hours=i), 60, 900))       # верные
    await fill(rows)
    border2 = await db.find_direction_border()
    check("граница не съехала на тихий час",
          border2 == base + timedelta(hours=31),
          str(border2))

    print()
    print("=== один час тяжёлой раздачи — не повод разворачивать ===")
    # Самая опасная подмена: человек честно раздавал час, и этот час выглядит
    # как ошибка сборщика. Принять его за границу значит перевернуть всё.
    rows = [(base + timedelta(hours=i), 60, 900) for i in range(60)]
    rows[45] = (base + timedelta(hours=45), 900, 60)
    await fill(rows)
    check("границы нет", await db.find_direction_border() is None,
          "одиночный выброс картины не создаёт")

    print()
    print("=== короткой истории не хватает, чтобы судить ===")
    rows = [(base + timedelta(hours=i), 900, 60) for i in range(5)]
    rows += [(base + timedelta(hours=i), 60, 900) for i in range(5, 12)]
    await fill(rows)
    check("границы нет", await db.find_direction_border() is None,
          "по десятку часов вывод делать нельзя")

    print()
    print("=== разворачивать нечего ===")
    # Свежая установка: сборщик исправен с первого дня.
    await fill([(base + timedelta(hours=i), 60, 900) for i in range(20)])
    check("границы нет", await db.find_direction_border() is None,
          "иначе ремонт испортил бы верные данные")

    print()
    print("=== всё перевёрнуто — молчим, а не разворачиваем вслепую ===")
    await fill([(base + timedelta(hours=i), 900, 60) for i in range(20)])
    check("границы нет", await db.find_direction_border() is None,
          "свежий час перевёрнут — значит сборщик ещё не починен")

    print()
    print("=== ремонт идёт сам и только один раз ===")
    import monitor
    await db.execute("DELETE FROM settings WHERE key='traffic_direction_repaired'")
    rows = [(base + timedelta(hours=i), 900, 60) for i in range(30)]
    rows += [(base + timedelta(hours=i), 60, 900) for i in range(30, 60)]
    await fill(rows)
    n = await monitor.repair_traffic_directions()
    check("починил при старте", n == 30, "строк: %s" % n)
    bad = await db.fetch_val(
        "SELECT COUNT(*) FROM traffic_hourly WHERE user_uuid='tb-1' "
        "AND bytes_in > bytes_out")
    check("перевёрнутых не осталось", bad == 0, "осталось: %s" % bad)
    check("отметка поставлена",
          bool(await db.get_setting("traffic_direction_repaired")))

    # Второй запуск не должен трогать ничего — даже если данные снова выглядят
    # перевёрнутыми. Отметка сильнее любого разбора.
    await fill([(base + timedelta(hours=i), 900, 60) for i in range(30)]
               + [(base + timedelta(hours=i), 60, 900) for i in range(30, 60)])
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
