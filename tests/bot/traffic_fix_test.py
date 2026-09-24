# -*- coding: utf-8 -*-
"""Разворот перевёрнутой истории трафика.

До исправления направлений сборщик писал отдачу в колонку приёма и наоборот:
любой качающий выглядел раздающим. Свежие часы пишутся верно, старые остались
зеркальными — пересчитать их нечем, в базе лежат уже сложенные суммы.

Перестановка колонок эту ошибку отменяет. Проверяется, что она:
  • трогает только строки старше границы, а свежие оставляет как есть;
  • меняет и байты, и пакеты — иначе доля отдачи считалась бы по мусору;
  • обратима: второй запуск возвращает как было.

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


async def row(uuid_val, hour):
    rows = await db.fetch_all(
        "SELECT bytes_in, bytes_out, packets_in, packets_out FROM traffic_hourly "
        "WHERE user_uuid=$1 AND hour=$2", uuid_val, hour)
    return dict(rows[0]) if rows else None


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'tf-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Трафиков','tf-1',TRUE)")

    border = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    old_hour = border - timedelta(hours=3)
    new_hour = border + timedelta(hours=1)

    # Старый час записан зеркально: отдача 900, приём 100.
    await db.add_hourly("tf-1", old_hour, 900, 100, 90, 10, 0)
    # Свежий — правильно: отдача 100, приём 900.
    await db.add_hourly("tf-1", new_hour, 100, 900, 10, 90, 0)

    print("=== до разворота ===")
    before_old = await row("tf-1", old_hour)
    check("старый час зеркальный", before_old["bytes_in"] == 900)

    print()
    print("=== разворот ===")
    count = await db.count_hourly_before(border)
    check("считаются только старые строки", count >= 1, "строк: %d" % count)
    await db.swap_hourly_directions(border)

    after_old = await row("tf-1", old_hour)
    after_new = await row("tf-1", new_hour)
    check("байты поменялись местами",
          after_old["bytes_in"] == 100 and after_old["bytes_out"] == 900,
          str(after_old))
    check("пакеты тоже",
          after_old["packets_in"] == 10 and after_old["packets_out"] == 90,
          "иначе доля отдачи считалась бы по мусору")
    check("свежий час не тронут",
          after_new["bytes_in"] == 100 and after_new["bytes_out"] == 900,
          str(after_new))

    print()
    print("=== обратимость ===")
    await db.swap_hourly_directions(border)
    again = await row("tf-1", old_hour)
    check("второй запуск вернул как было", again["bytes_in"] == 900,
          "поэтому действие и кнопкой, а не само при обновлении")
    await db.swap_hourly_directions(border)

    await db.execute("DELETE FROM users WHERE uuid LIKE 'tf-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
