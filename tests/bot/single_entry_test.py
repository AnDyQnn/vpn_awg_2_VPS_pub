# -*- coding: utf-8 -*-
"""Вход Xray один — запасных на 2053 и 2083 больше нет.

Раньше входов было три: основной на 443 и два запасных с чужими масками
(wildberries.ru на 2053, ozon.ru на 2083). Задумка была такая: заблокируют одну
маску — приложение перейдёт на живой вход. Запасные убраны по решению владельца:
они держались на чужих сайтах, за которыми никто не следил, а два лишних
открытых порта HTTPS — лишние приметы.

Проверяется, что убраны они везде, а не только из списка:
  • вход один, и это основной из настроек;
  • в конфиге узла ровно один вход для людей, и ни 2053, ни 2083 там нет;
  • владелец сменил порт основного — запасной на 443 не появляется сам;
  • в подписке одна строка, без приписки «запасной»;
  • разовая ссылка совпадает со строкой подписки.
"""
import asyncio
import base64
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True
GONE = (2053, 2083)


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'se-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'se-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Одновход','se-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('se-1','x-se','tok-se')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("xray_private_key", "PRIV"), ("server_host", "1.2.3.4"),
                     ("xray_dest", ""), ("xray_port", "")):
        await db.set_setting(key, val)

    print("=== входы ===")
    ways = await xray.entries()
    for port, dest in ways:
        print("   %-6s %s" % (port, dest))
    check("вход ровно один", len(ways) == 1, "%d" % len(ways))
    check("это основной", ways[0] == (xray.DEFAULT_PORT, xray.DEFAULT_DEST),
          str(ways[0]))
    check("списка запасных в коде нет",
          not hasattr(xray, "DEFAULT_ENTRIES"),
          "оставленный список однажды снова начнут читать")

    print()
    print("=== конфиг узла ===")

    async def fake_ips():
        return {"se-1": "10.13.13.9"}

    xray.peer_ip_map = fake_ips
    config, addresses, note = await xray.build_config()
    # Служебный вход счётчиков — не про людей: слушает петлю, без масок.
    ins = [i for i in config["inbounds"] if i.get("protocol") == "vless"]
    check("вход для людей один", len(ins) == 1, "%d" % len(ins))
    check("и он на основном порту",
          ins and ins[0]["port"] == xray.DEFAULT_PORT,
          str([i["port"] for i in ins]))
    all_ports = [i.get("port") for i in config["inbounds"]]
    check("запасных портов в конфиге нет",
          not any(p in GONE for p in all_ports), str(all_ports))

    print()
    print("=== имена разрешает наш резолвер, а не провайдер ===")
    # Без этого сервер разрешал имена системным DNS контейнера — российским, и
    # на живом узле www.youtube.com получал NXDOMAIN.
    dns = config.get("dns") or {}
    check("DNS сервера указан", xray.SERVER_DNS in (dns.get("servers") or []),
          str(dns))
    frees = [o for o in config["outbounds"] if o.get("protocol") == "freedom"]
    check("все выходы разрешают имена через него",
          frees and all((o.get("settings") or {}).get("domainStrategy") == "UseIPv4"
                        for o in frees),
          ", ".join("%s=%s" % (o.get("tag"), (o.get("settings") or {}).get("domainStrategy"))
                    for o in frees))

    print()
    print("=== сменили порт основного ===")
    # Раньше при основном не на 443 список дописывал 443 с маской avito
    # «запасным». Теперь ничего не дописывается: вход один, какой задали.
    await db.set_setting("xray_port", "8443")
    moved = await xray.entries()
    check("вход по-прежнему один", len(moved) == 1, str(moved))
    check("и он на заданном порту", moved and moved[0][0] == 8443, str(moved))
    await db.set_setting("xray_port", "")

    print()
    print("=== что уходит человеку ===")
    links = await xray.profile_links("se-1")
    check("ссылка одна", len(links) == 1, "%d" % len(links))
    name = links[0].split("#", 1)[1] if links and "#" in links[0] else ""
    check("имя — просто имя человека", name == "Одновход", name)
    check("приписки «запасной» нет", "запасной" not in name)
    check("запасных портов в ссылке нет",
          not any(":%d?" % p in links[0] for p in GONE) if links else False)

    body = await xray.subscription_body("tok-se")
    decoded = base64.b64decode(body).decode()
    lines = [x for x in decoded.split(chr(10)) if x]
    check("в подписке одна строка", len(lines) == 1, "%d" % len(lines))
    check("разовая ссылка совпадает с ней",
          lines and (await xray.profile_link("se-1")) == lines[0])

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'se-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'se-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
