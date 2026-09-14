# -*- coding: utf-8 -*-
"""Имена внутри туннеля: разбор, привязка к человеку, раскладка на узел."""
import asyncio
import json

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

    def post(self, url, json=None, timeout=None):
        FakeSession.last = json["names"]
        return FakeResp({"status": "ok", "names": len(json["names"])})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dn-%'")
    for uid, name in (("dn-1", "Ника"), ("dn-2", "Папа")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    dn.api_session = lambda: FakeSession()

    print("=== разбор введённого ===")
    assert dn.normalize("дом") == ("дом.vpn", None)
    assert dn.normalize("  KINO  ")[0] == "kino.vpn"
    assert dn.normalize("дом.vpn")[0] == "дом.vpn"
    assert dn.normalize("")[1]
    assert dn.normalize("что.то.ещё")[1], "точки внутри принимать нельзя"
    assert dn.normalize("-плохо")[1], "имя не может начинаться с дефиса"
    assert dn.normalize("x" * 40)[1], "слишком длинное имя не принимаем"
    print("одно слово, зона добавляется сама, мусор отбит: ок")

    print("\n=== русские буквы доезжают как надо ===")
    puny = dn.to_punycode("дом.vpn")
    print(" ", puny)
    assert puny.startswith("xn--") and puny.endswith(".vpn")
    assert dn.to_punycode("kino.vpn") == "kino.vpn"
    print("переводится только то, что нужно: ок")

    print("\n=== имя на человека ===")
    async def ips():
        return {"dn-1": "10.13.13.6", "dn-2": "10.13.13.7"}
    import acl
    acl.peer_ip_map = ips

    await db.set_dns_name("дом.vpn", target_uuid="dn-1")
    await db.set_dns_name("papa.vpn", target_uuid="dn-2")
    await db.set_dns_name("узел.vpn", target_ip="10.13.13.1")

    ok, msg = await dn.apply_names("тест")
    assert ok, msg
    table = FakeSession.last
    print(" ", {k: v for k, v in table.items() if not k.startswith("xn--")})
    assert table["дом.vpn"] == "10.13.13.6"
    assert table["papa.vpn"] == "10.13.13.7"
    assert table["узел.vpn"] == "10.13.13.1"
    print("адрес человека подставился, ручной адрес остался: ок")

    print("\n=== узлу уходят обе формы имени ===")
    assert table[dn.to_punycode("дом.vpn")] == "10.13.13.6"
    assert table[dn.to_punycode("узел.vpn")] == "10.13.13.1"
    print("и русская, и punycode: ок")

    print("\n=== адрес человека сменился — имя переехало само ===")
    async def ips2():
        return {"dn-1": "10.13.13.90", "dn-2": "10.13.13.7"}
    acl.peer_ip_map = ips2
    await dn.apply_names("смена адреса")
    assert FakeSession.last["дом.vpn"] == "10.13.13.90", FakeSession.last
    print("имя ведёт на новый адрес без вмешательства: ок")

    print("\n=== человек без адреса не ломает раскладку ===")
    await db.set_dns_name("ничей.vpn", target_uuid="dn-1")
    async def ips3():
        return {"dn-2": "10.13.13.7"}
    acl.peer_ip_map = ips3
    ok, msg = await dn.apply_names("без адреса")
    assert ok, msg
    assert "дом.vpn" not in FakeSession.last
    assert "papa.vpn" in FakeSession.last
    print(" ", msg)
    print("пропущен только тот, у кого нет адреса: ок")

    print("\n=== удаление человека уносит его имя ===")
    await db.execute("DELETE FROM users WHERE uuid='dn-2'")
    rows = {r["name"] for r in await db.list_dns_names()}
    assert "papa.vpn" not in rows, rows
    assert "узел.vpn" in rows, "ручное имя не должно зависеть от людей"
    print("имя человека ушло с ним, ручное осталось: ок")

    print("\n=== переименование сохраняет цель ===")
    await db.rename_dns_name("узел.vpn", "panel.vpn")
    row = await db.get_dns_name("panel.vpn")
    assert row and row["target_ip"] == "10.13.13.1"
    assert await db.get_dns_name("узел.vpn") is None
    print("цель на месте, старое имя исчезло: ок")

    print("\n=== когда имён не осталось, таблица пуста ===")
    for r in await db.list_dns_names():
        await db.delete_dns_name(r["name"])
    await dn.apply_names("очистка")
    # Служебное имя заводится один раз при первом запуске. Удалили — значит
    # удалили: система не возвращает то, что владелец убрал сам.
    assert FakeSession.last == {}, FakeSession.last
    print("узлу уходит пусто — он снимет заворот сам: ок")

    # Раскладку кладём на диск: узловой тест применит РОВНО её, а не
    # придуманную руками — иначе проверялся бы код, а не стык.
    await db.set_dns_name('дом.vpn', target_uuid='dn-1')
    await db.set_dns_name('panel.vpn', target_ip='10.13.13.1')
    acl.peer_ip_map = ips
    await dn.apply_names('для узлового теста')
    import os
    if os.path.isdir('/out'):
        import json as _json
        with open('/out/dns_names_payload.json', 'w', encoding='utf-8') as f:
            _json.dump({'names': FakeSession.last}, f, ensure_ascii=False)
        print('раскладка имён сохранена для узлового теста')

    await db.execute("DELETE FROM users WHERE uuid LIKE 'dn-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
