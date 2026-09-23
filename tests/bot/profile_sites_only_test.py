# -*- coding: utf-8 -*-
"""В профиле Xray — только сайты с вкладки сплит-туннеля. Никаких адресов.

Правило владельца. Раньше профиль собирался по логике AmneziaWG и был забит
адресами, которых никто не заводил: подсети, которые бот сам вывел из доменов
обхода; вся 10.0.0.0/8 без нашей /24 — то есть адреса вокруг самого VPN шли
напрямую; адрес узла; 0.0.0.0/0 в туннельные; и DNS на внутренний 10.13.13.1,
которого для телефона на Xray не существует — он внутри туннеля не сидит.

Нужные адреса владелец заводит сам. Проверяем, что в профиль не просачивается
ни одного адреса — ни из общего списка, ни из личных записей ключа, ни из кода.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing as H                           # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def has_address(value):
    return H._is_net(value)


async def main():
    await db.connect()
    # Общий список: сайт и запись, заведённая адресом.
    await db.add_bypass_exclusion("sites-only.example", "203.0.113.0/24", bump=False)
    await db.add_bypass_exclusion("198.51.100.7", "198.51.100.0/24", bump=False)
    # Узел знает свой адрес — раньше он уходил в профиль первой строкой.
    await db.set_setting("server_host", "203.0.113.55")

    prof = await H.profile()
    print("=== что в профиле ===")
    for k in sorted(prof):
        if k != "LastUpdated":
            print("   %-18s %s" % (k, str(prof[k])[:90]))

    print()
    print("=== адресов нет ни в одном поле ===")
    # Списки присутствуют явно и пустые: иначе приложение дополнит их своими
    # частными сетями по умолчанию (10.0.0.0/8, 192.168.0.0/16 …).
    for field in ("DirectIp", "ProxyIp", "BlockIp", "BlockSites", "ProxySites"):
        check("%s есть и пуст" % field, prof.get(field) == [], str(prof.get(field))[:80])
    for field in ("DirectSites", "ProxySites"):
        vals = prof.get(field) or []
        check("в %s только имена" % field, not any(has_address(v) for v in vals),
              str([v for v in vals if has_address(v)]))

    print()
    print("=== сайты на месте ===")
    check("сайт из вкладки сплит-туннеля попал", "sites-only.example" in prof["DirectSites"])
    check("запись-адрес в сайты не попала", "198.51.100.7" not in prof["DirectSites"])

    print()
    print("=== DNS не внутренний ===")
    check("DNS через туннель — публичный, не 10.13.13.1",
          prof["RemoteDNSIP"] != "10.13.13.1" and not prof["RemoteDNSIP"].startswith("10."),
          prof["RemoteDNSIP"])
    check("и это DoH", prof["RemoteDNSType"] == "DoH" and prof["RemoteDNSDomain"].startswith("https://"),
          prof["RemoteDNSType"] + " " + prof["RemoteDNSDomain"])

    print()
    print("=== имя не разрешается заранее ради сверки с адресами ===")
    check("DomainStrategy AsIs", prof["DomainStrategy"] == "AsIs", prof["DomainStrategy"])

    print()
    print("=== личные записи ключа: то, что владелец вписал сам ===")
    await db.execute("DELETE FROM users WHERE uuid='so-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Сайты','so-1',TRUE)")
    await db.add_peer_route("so-1", "10.50.0.0/16", "direct")
    await db.add_peer_route("so-1", "personal.example", "direct")
    await db.add_peer_route("so-1", "10.13.13.36/32", "proxy")
    await db.add_peer_route("so-1", "proxied.example", "proxy")
    mine = await H.profile("so-1")
    check("личный сайт напрямую — в сайтах", "personal.example" in mine["DirectSites"])
    check("личный сайт через VPN — в туннельных сайтах",
          "proxied.example" in (mine.get("ProxySites") or []))
    # «Нужные адреса настрою сам»: адреса, вписанные вручную в личные маршруты
    # ключа, идут в профиль ровно как вписаны — и больше ни одного.
    check("вписанный адрес напрямую — на месте, и он один",
          mine.get("DirectIp") == ["10.50.0.0/16"], str(mine.get("DirectIp")))
    check("вписанный адрес через VPN — на месте, и он один",
          mine.get("ProxyIp") == ["10.13.13.36/32"], str(mine.get("ProxyIp")))
    check("в сайты адреса не попали", "10.50.0.0/16" not in mine["DirectSites"])

    await db.execute("DELETE FROM users WHERE uuid='so-1'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
