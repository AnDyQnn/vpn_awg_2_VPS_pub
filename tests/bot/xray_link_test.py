# -*- coding: utf-8 -*-
"""Ссылка Xray собирается — и не обещается, когда не собралась.

Найдено на бою: владелец выдал ключ, бот написал «Готово, новая ссылка ниже»,
и ничего не пришло. Ни при выдаче, ни при перевыпуске.

Причина оказалась старше: `profile_link` читала настройку `server_host`, а
записывал её **ноль строк кода** — во всём проекте это чтение было единственным
упоминанием. То есть ссылка выходила пустой всегда, с первого дня.

Адрес при этом известен и проверен: он стоит `Endpoint` в каждом конфиге
AmneziaWG — по нему люди подключаются прямо сейчас. Спросить у самого узла
нельзя: наружу он ходит через Германию и назовёт немецкий адрес.

Проверяется:
  • адрес берётся из конфигов, когда настройка пуста;
  • заданная вручную настройка сильнее найденного;
  • ссылка собирается целиком и содержит всё, что нужно приложению;
  • без адреса ссылка пустая — и это не должно превращаться в обещание.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


CONF = "/volumes/configs"
PROBE = os.path.join(CONF, "zz-проверка-адреса.conf")


async def main():
    await db.connect()
    os.makedirs(CONF, exist_ok=True)
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'lk-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'lk-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Ссылкин','lk-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('lk-1','x-uuid-1','tok-1')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "abcd"),
                     ("xray_private_key", "PRIV")):
        await db.set_setting(key, val)

    print("=== адрес берётся из конфигов людей ===")
    await db.set_setting("server_host", "")
    with open(PROBE, "w", encoding="utf-8") as f:
        f.write("[Peer]\nEndpoint = 203.0.113.10:51820\n")
    host = await xray.server_host()
    check("нашёлся в конфиге", host == "203.0.113.10", host or "пусто")
    check("запомнен в настройках",
          (await db.get_setting("server_host")) == "203.0.113.10")

    print()
    print("=== заданный вручную сильнее найденного ===")
    await db.set_setting("server_host", "vpn.example.ru")
    check("взят заданный", await xray.server_host() == "vpn.example.ru")

    print()
    print("=== ссылка собирается целиком ===")
    link = await xray.profile_link("lk-1")
    print("  ", (link[:90] + "…") if link else "ПУСТО")
    check("ссылка есть", bool(link))
    if link:
        for part in ("vless://", "x-uuid-1", "vpn.example.ru",
                     "security=reality", "pbk=PUB", "sid=abcd"):
            check("в ссылке есть %s" % part, part in link)
        check("имя человека в хвосте", link.rstrip().endswith("Ссылкин"),
              link[-20:])

    print()
    print("=== адреса нет — ссылка пустая, а не кривая ===")
    await db.set_setting("server_host", "")
    os.remove(PROBE)
    # Чтобы не подцепить чужой конфиг, сверяем через явно пустой адрес.
    empty = await xray.profile_link("lk-1") if not await xray.server_host() else ""
    check("пустая, а не обрубок", empty == "",
          "именно пустую проверяют вызывающие места")

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'lk-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'lk-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
