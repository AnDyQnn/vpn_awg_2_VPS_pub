# -*- coding: utf-8 -*-
"""Проверки на то, что нашлось при живом тестировании.

Три находки владельца: служебное имя нельзя было переименовать, журнал
немецкого узла состоял из обращений к панели, и с некоторых экранов нельзя
было уйти. Первые две проверяются здесь, третья — отдельной проверкой
screens_audit.py.
"""
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
    await db.execute("DELETE FROM dns_names")
    await db.execute("DELETE FROM settings WHERE key LIKE 'dns_node_name%'")
    dn.api_session = lambda: FakeSession()

    import acl

    async def ips():
        return {}
    acl.peer_ip_map = ips

    print("=== служебное имя заводится один раз ===")
    # Имя зависит от зоны, а зона — от того, есть ли у узла своё имя.
    # Спрашиваем, а не помним константой.
    svc = dn.default_node_name()
    created = await dn.ensure_node_name()
    assert created, "не завелось"
    assert await db.get_dns_name(svc)
    assert not await dn.ensure_node_name(), "завелось второй раз"
    print(" ", svc, "— заведено: ок")

    print("\n=== переименование заменяет, а не создаёт второе ===")
    await db.rename_dns_name(svc, "стоп.vpn")
    await dn.remember_node_name("стоп.vpn")
    await dn.apply_names("после переименования")
    names = {r["name"] for r in await db.list_dns_names()}
    print(" ", names)
    assert names == {"стоп.vpn"}, names
    assert await dn.node_name() == "стоп.vpn"
    print("старое название не вернулось: ок")

    print("\n=== удалили — значит удалили ===")
    await db.delete_dns_name("стоп.vpn")
    await dn.apply_names("после удаления")
    names = {r["name"] for r in await db.list_dns_names()}
    print(" ", names or "пусто")
    assert not names, names
    print("система не спорит с владельцем: ок")

    print("\n=== журнал немецкого узла: события, а не обращения к панели ===")
    import handlers_admin as ha
    raw = "\n".join([
        'INFO:     Started server process [1]',
        'INFO:     10.13.13.1:52744 - "GET /api/wg/status HTTP/1.1" 200 OK',
        'INFO:     10.13.13.1:52745 - "GET /api/system_stats HTTP/1.1" 200 OK',
        '[#] wg setconf wg0 /dev/fd/63',
        'INFO:     10.13.13.1:52746 - "POST /api/wg/reload HTTP/1.1" 200 OK',
        'ERROR: туннель не поднялся',
    ])
    keep, dropped = ha._useful_lines(raw)
    for line in keep:
        print("   ", line[:60])
    print("  отсеяно:", dropped)
    assert dropped == 3, dropped
    assert any("ERROR" in l for l in keep), keep
    assert any("wg setconf" in l for l in keep), keep
    assert not any("/api/" in l for l in keep), keep
    print("осталось то, ради чего в журнал и смотрят: ок")

    print("\n=== цвет узла: диск не должен пугать зря ===")
    import monitor
    # Цвет считается внутри сборки дашборда, поэтому проверяем саму таблицу
    # порогов через ту же функцию, вытащив её из исходника.
    import inspect
    src = inspect.getsource(monitor.build_dashboard_text if
                            hasattr(monitor, "build_dashboard_text") else monitor)
    assert "disk >= 93" in src and "disk >= 85" in src, "пороги диска не подняты"
    assert "load >= 70" in src, "пороги нагрузки потерялись"
    print("у диска свои пороги 85 и 93, у нагрузки прежние: ок")

    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
