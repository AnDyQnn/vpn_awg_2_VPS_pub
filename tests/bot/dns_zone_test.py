# -*- coding: utf-8 -*-
"""Переезд имён из выдуманной зоны в настоящее имя узла.

Проверяется главное, из-за чего этот переезд вообще опасен: имена меняются не
сами по себе, на них ссылаются правила доступа. Уехавшее имя с оставшимся
позади правилом выглядит настроенным, а доступа не даёт — и понять это можно
только сверкой вручную.
"""
import asyncio
import json
import os

from database import db
import dnsnames as dn


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def text(self):
        return json.dumps(self._p)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    last = None

    last_zone = None

    def post(self, url, json=None, timeout=None):
        FakeSession.last = json["names"]
        FakeSession.last_zone = json.get("zone")
        return FakeResp({"status": "ok"})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def set_domain(value):
    if value:
        os.environ["PUBLIC_DOMAIN"] = value
    else:
        os.environ.pop("PUBLIC_DOMAIN", None)


async def main():
    await db.connect()
    for r in await db.list_dns_names():
        await db.delete_dns_name(r["name"])
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3)",
                     dn.ZONE_KEY, dn.NODE_NAME_KEY, dn.NODE_NAME_DONE)
    await db.execute("DELETE FROM roles WHERE name='зонатест'")

    async def _ips():
        return {}

    dn.api_session = lambda: FakeSession()
    import acl
    acl.peer_ip_map = _ips

    print("=== без имени узла всё как было ===")
    set_domain("")
    assert dn.zone() == "vpn", dn.zone()
    assert dn.normalize("дом") == ("дом.vpn", None)
    assert dn.default_node_name() == "закрыто.vpn"
    print("зона местная, имена прежние: ок")

    print("\n=== имя узла появилось — зона стала настоящей ===")
    set_domain("example.ru")
    assert dn.zone() == "example.ru", dn.zone()
    assert dn.normalize("дом") == ("дом.example.ru", None)
    # Точки в настоящем домене есть, и прежний разбор отвергал бы своё же имя.
    assert dn.normalize("дом.example.ru") == ("дом.example.ru", None)
    assert dn.normalize("что.то.ещё")[1], "чужие точки принимать по-прежнему нельзя"
    print("зона из окружения, своё полное имя принимается: ок")

    print("\n=== ссылку целиком тоже принимаем ===")
    set_domain("https://example.ru/")
    assert dn.zone() == "example.ru", dn.zone()
    set_domain("example.ru")

    print("\n=== мусор в окружении не делает зону мусорной ===")
    set_domain("не домен вовсе")
    assert dn.zone() == "vpn", "непригодное имя не должно становиться зоной"
    set_domain("")

    print("\n=== переезд уводит имена и правила вместе ===")
    await db.set_dns_name("дом.vpn", target_ip="10.13.13.5")
    await db.set_dns_name("kino.vpn", target_ip="10.13.13.6")
    await db.set_setting(dn.ZONE_KEY, "vpn")
    await db.set_setting(dn.NODE_NAME_KEY, "закрыто.vpn")
    await db.set_setting(dn.NODE_NAME_DONE, "1")

    role_id = await db.create_role("зонатест")
    await db.add_role_grant(role_id, name="дом.vpn", proto="tcp", port=80)

    set_domain("example.ru")
    moved, clashed = await dn.migrate_zone()
    print("  переехало:", moved, "осталось:", clashed)
    assert moved == 2, moved
    assert not clashed
    names = {r["name"] for r in await db.list_dns_names()}
    assert names == {"дом.example.ru", "kino.example.ru"}, names
    assert (await db.get_dns_name("дом.example.ru"))["target_ip"] == "10.13.13.5"

    grants = await db.get_role_grants(role_id)
    assert grants[0]["name"] == "дом.example.ru", grants
    print("имя переехало, правило доступа уехало за ним: ок")

    print("\n=== служебное имя не раздваивается ===")
    assert await dn.node_name() == "закрыто.example.ru", await dn.node_name()
    await dn.ensure_node_name()
    names = {r["name"] for r in await db.list_dns_names()}
    assert "закрыто.vpn" not in names, names
    print("прежнее не завелось заново: ок")

    print("\n=== второй раз переезжать нечего ===")
    moved, clashed = await dn.migrate_zone()
    assert moved == 0 and not clashed
    print("повторный вызов ничего не трогает: ок")

    print("\n=== занятое имя не затирается молча ===")
    await db.set_dns_name("дом.vpn", target_ip="10.13.13.9")
    await db.set_setting(dn.ZONE_KEY, "vpn")
    moved, clashed = await dn.migrate_zone()
    print("  ", moved, clashed)
    assert moved == 0, moved
    assert clashed == ["дом.vpn"], clashed
    assert (await db.get_dns_name("дом.example.ru"))["target_ip"] == "10.13.13.5", \
        "чужая цель не должна была подмениться"
    await db.delete_dns_name("дом.vpn")
    await db.set_setting(dn.ZONE_KEY, "example.ru")

    print("\n=== раскладка на узел идёт уже в новой зоне ===")
    ok, msg = await dn.apply_names("тест переезда")
    assert ok, msg
    # В таблице три вида записей: полное имя, его punycode и короткая форма.
    # Короткая — удобство поверх: полное остаётся главным, на него ссылаются
    # правила доступа.
    for n in FakeSession.last:
        assert (n.endswith("example.ru") or n.startswith("xn--")
                or "." not in n), (n, FakeSession.last)
    print("  ", sorted(n for n in FakeSession.last if not n.startswith("xn--")))
    print("узел получил имена в настоящей зоне: ок")

    print("\n=== короткое имя работает наравне с полным ===")
    # Третий уровень в адресной строке каждый раз — ровно та мелочь, из-за
    # которой удобной вещью перестают пользоваться.
    table = FakeSession.last
    print("  ", sorted(k for k in table if not k.startswith("xn--")))
    assert table.get("дом") == table.get("дом.example.ru"), table
    assert table.get("kino") == table.get("kino.example.ru"), table
    assert "дом.example.ru" in table, "полное имя обязано остаться главным"
    print("отвечает и на «дом», и на «дом.example.ru»: ок")

    print("\n=== короткое идёт за своим полным ===")
    await db.set_dns_name("kino.example.ru", target_ip="10.13.13.77")
    table2, _ = await dn.resolve_all()
    assert table2["kino.example.ru"] == "10.13.13.77", table2
    assert table2["kino"] == "10.13.13.77", table2.get("kino")
    print("сменилась цель — сменилось и короткое: ок")

    print("\n=== зона уезжает на узел вместе с именами ===")
    # Из неё узел делает поисковый домен для новых конфигов.
    assert FakeSession.last_zone == "example.ru", FakeSession.last_zone
    print("  зона:", FakeSession.last_zone)
    print("узел знает, чем достраивать короткое имя: ок")

    print("\n=== имя убрали — возвращаемся в местную зону ===")
    set_domain("")
    moved, clashed = await dn.migrate_zone()
    names = {r["name"] for r in await db.list_dns_names()}
    assert all(n.endswith(".vpn") for n in names), names
    print("  ", sorted(names))
    print("обратный путь работает, имена не теряются: ок")

    await db.execute("DELETE FROM roles WHERE name='зонатест'")
    for r in await db.list_dns_names():
        await db.delete_dns_name(r["name"])
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
