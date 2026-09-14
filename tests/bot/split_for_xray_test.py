# -*- coding: utf-8 -*-
"""Исключения сплит-туннеля доезжают до Xray.

На AmneziaWG перечисленные адреса просто не входят в туннель: запрос к
Госуслугам идёт с домашнего адреса, и они его принимают. На Xray в профиле, что
мы отдаём, нет ни слова про маршруты — всё идёт через узел, то есть с адреса
хостинга. У владельца в исключениях Госуслуги с ЕСИА, ВТБ и ещё пять записей:
именно те, кому адрес хостинга не нравится.

Серверной стороной это не лечится: трафик уже пришёл на узел. Значит правила
должны попасть в приложение, а ссылка их нести не умеет — умеет готовый
профиль.

Проверяется:
  • профиль настоящий, без выдуманных полей: каналы наружу описаны полностью;
  • исключения в нём есть и ведут мимо туннеля;
  • домашняя сеть тоже мимо — до принтера ходят напрямую;
  • запасные входы на месте и здесь;
  • приостановленному не отдаётся ничего;
  • обычная подписка при этом не изменилась ни на байт.
"""
import asyncio
import base64
import json
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sx-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sx-%'")
    await db.execute("DELETE FROM bypass_exclusions WHERE domain LIKE 'тест-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Сплитов','sx-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('sx-1','x-sx','tok-sx')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    await db.add_bypass_exclusion("тест-госуслуги.ru", "203.0.113.0/24",
                                  note="проверка", source="test", bump=False)

    print("=== профиль собирается ===")
    raw = await xray.subscription_config("tok-sx")
    check("профиль не пуст", bool(raw))
    cfg = json.loads(raw)
    check("это разбираемый JSON", isinstance(cfg, dict))

    print()
    print("=== каналы наружу описаны по-настоящему ===")
    outs = cfg["outbounds"]
    proxies = [o for o in outs if o.get("protocol") == "vless"]
    direct = [o for o in outs if o.get("protocol") == "freedom"]
    check("каналов столько, сколько входов",
          len(proxies) == len(await xray.entries()), "%d" % len(proxies))
    check("прямой канал есть", len(direct) == 1,
          "без него исключениям некуда идти")
    first = proxies[0]
    v = first["settings"]["vnext"][0]
    check("адрес узла на месте", v["address"] == "1.2.3.4", v["address"])
    check("личный ключ человека на месте", v["users"][0]["id"] == "x-sx")
    r = first["streamSettings"]["realitySettings"]
    check("маска на месте", bool(r.get("serverName")), r.get("serverName"))
    check("открытый ключ на месте", r.get("publicKey") == "PUB")
    check("никаких выдуманных полей",
          set(first) <= {"tag", "protocol", "settings", "streamSettings"},
          ", ".join(sorted(first)))

    print()
    print("=== исключения ведут мимо туннеля ===")
    rules = cfg["routing"]["rules"]
    direct_rules = [x for x in rules if x.get("outboundTag") == "direct"]
    check("правила мимо туннеля есть", bool(direct_rules))
    all_ips = [ip for x in direct_rules for ip in (x.get("ip") or [])]
    check("наше исключение в них", "203.0.113.0/24" in all_ips,
          ", ".join(all_ips[:4]))
    check("домашняя сеть тоже мимо", "geoip:private" in all_ips,
          "до принтера и роутера ходят напрямую")

    print()
    print("=== приостановленному не отдаётся ничего ===")
    await db.execute("UPDATE users SET is_active=FALSE WHERE uuid='sx-1'")
    check("профиль пуст", await xray.subscription_config("tok-sx") == "")
    check("и обычная подписка тоже",
          await xray.subscription_body("tok-sx") == "")
    await db.execute("UPDATE users SET is_active=TRUE WHERE uuid='sx-1'")

    print()
    print("=== обычная подписка не изменилась ===")
    body = await xray.subscription_body("tok-sx")
    decoded = base64.b64decode(body).decode()
    check("это по-прежнему список ссылок",
          all(l.startswith("vless://") for l in decoded.splitlines()),
          "%d строк" % len(decoded.splitlines()))
    check("и там столько же входов",
          len(decoded.splitlines()) == len(await xray.entries()))

    await db.execute("DELETE FROM bypass_exclusions WHERE domain LIKE 'тест-%'")
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sx-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sx-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
