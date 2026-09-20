# -*- coding: utf-8 -*-
"""Разворот перевёрнутой истории трафика и профиль по адресу для скрипта.

До исправления направлений сборщик писал отдачу в колонку приёма и наоборот:
любой качающий выглядел раздающим. Свежие часы пишутся верно, старые остались
зеркальными — пересчитать их нечем, в базе лежат уже сложенные суммы.

Перестановка колонок эту ошибку отменяет. Проверяется, что она:
  • трогает только строки старше границы, а свежие оставляет как есть;
  • меняет и байты, и пакеты — иначе доля отдачи считалась бы по мусору;
  • обратима: второй запуск возвращает как было.

Заодно проверяется ручка профиля: скрипту нужен JSON, а не ссылка для
приложения, и ходит он по тому же личному токену, что и подписка.
"""
import asyncio
import json
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

    print()
    print("=== профиль по адресу для скрипта ===")
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'tf-%'")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('tf-1','x-tf','tok-tf')")
    await db.add_peer_route("tf-1", "10.77.0.0/16", "direct")

    import subscription as S

    class Req:
        match_info = {"token": "tok-tf"}

    resp = await S.handle_routing(Req())
    check("отдаётся", resp.status == 200, str(resp.status))
    check("это JSON", "json" in resp.content_type, resp.content_type)
    profile = json.loads(resp.body.decode())
    check("личная сеть ключа внутри", "10.77.0.0/16" in profile["DirectIp"],
          "скрипту нужен профиль именно этого ключа")
    # Целиком 10.0.0.0/8 в списке больше нет, и это сделано нарочно: внутри
    # него лежит сеть самого туннеля, а прямые правила приложение применяет
    # РАНЬШЕ туннельных. Пока сеть узла оставалась внутри «домашнего»
    # диапазона, запросы к нашему резолверу уходили мимо туннеля. Поэтому
    # диапазон приезжает кусками, с вырезанной серединой.
    import ipaddress
    direct = [ipaddress.ip_network(x) for x in profile["DirectIp"]
              if ":" not in x]
    home = ipaddress.ip_address("10.200.0.1")
    node = ipaddress.ip_address("10.13.13.1")
    check("домашний диапазон на месте", any(home in n for n in direct),
          str(profile["DirectIp"])[:120])
    check("а сеть туннеля из него вырезана",
          not any(node in n for n in direct),
          "иначе запросы к нашему резолверу уйдут мимо туннеля")

    class Bad:
        match_info = {"token": "нет-такого"}
        # Промахи считаются по адресу: с него берут, кого закрывать на час.
        remote = "198.51.100.5"

    check("чужой токен не обслуживается",
          (await S.handle_routing(Bad())).status == 404)

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'tf-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'tf-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
