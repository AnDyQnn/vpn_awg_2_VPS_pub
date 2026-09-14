# -*- coding: utf-8 -*-
"""Жизненный цикл на Xray: отключает сервер, а не ссылка."""
import asyncio
import json

from database import db
import xray


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
    """Узел: запоминает последний конфиг и поднятые адреса."""
    last = {}
    addrs = []
    applies = 0

    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV", "password": "PUB"})
        if url.endswith("/xray/config"):
            FakeSession.last = json["config"]
            FakeSession.addrs = json.get("addresses") or []
            FakeSession.applies += 1
            return FakeResp({"status": "ok", "note": "запущен"})
        return FakeResp({}, 404)

    def get(self, url, timeout=None):
        return FakeResp([], 200)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def emails():
    return {c["email"] for c in FakeSession.last["inbounds"][0]["settings"]["clients"]}


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'lf-%'")
    for uid, name in (("lf-1", "Ника"), ("lf-2", "Папа")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    xray.api_session = lambda: FakeSession()

    async def ips():
        return {"lf-1": "10.13.13.6", "lf-2": "10.13.13.7"}
    xray.peer_ip_map = ips
    await db.set_setting("server_host", "203.0.113.9")

    enabled = {"on": True}

    async def status():
        return {"awg": {"enabled": True, "up": True, "peers": 2},
                "xray": {"enabled": enabled["on"], "up": True, "connections": 0}}
    xray.status = status

    ok, token = await xray.issue("lf-1")
    assert ok
    ok, _ = await xray.issue("lf-2")
    assert ok
    print("=== оба выданы ===")
    print(emails(), FakeSession.addrs)
    assert emails() == {"lf-1", "lf-2"}
    assert sorted(FakeSession.addrs) == ["10.13.13.134", "10.13.13.135"]
    print("в конфиге оба, адреса подняты: ок")

    print("\n=== пауза убирает человека с сервера ===")
    await db.execute("UPDATE users SET is_active=FALSE WHERE uuid='lf-1'")
    ok, msg = await xray.sync_person("пауза")
    print(msg)
    assert ok
    assert emails() == {"lf-2"}, emails()
    assert FakeSession.addrs == ["10.13.13.135"], FakeSession.addrs
    print("убран из конфига, адрес снят: ок")

    body = await xray.subscription_body(token)
    assert body == "", "подписка приостановленного обязана быть пустой"
    print("подписка тоже пуста — но отключил именно сервер: ок")

    print("\n=== разморозка возвращает ===")
    await db.execute("UPDATE users SET is_active=TRUE WHERE uuid='lf-1'")
    ok, _ = await xray.sync_person("разморозка")
    assert ok and emails() == {"lf-1", "lf-2"}, emails()
    assert await xray.subscription_body(token) != ""
    print("вернулся и в конфиг, и в подписку: ок")

    print("\n=== удаление убирает адрес ===")
    await db.execute("DELETE FROM users WHERE uuid='lf-2'")
    ok, _ = await xray.sync_person("человек удалён")
    assert ok and emails() == {"lf-1"}, emails()
    assert FakeSession.addrs == ["10.13.13.134"], FakeSession.addrs
    print("ушёл вместе с адресом: ок")

    print("\n=== при выключенном протоколе узел не дёргается ===")
    enabled["on"] = False
    before = FakeSession.applies
    ok, msg = await xray.sync_person("пауза")
    print(msg)
    assert not ok and FakeSession.applies == before
    print("лишних обращений нет: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'lf-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
