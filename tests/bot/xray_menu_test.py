# -*- coding: utf-8 -*-
"""Главное меню: разбивка «на связи» по протоколам."""
import asyncio
import json
import time

from database import db
import xray
import handlers_admin as ha


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
    def get(self, url, timeout=None):
        if url.endswith("/status"):
            return FakeResp({"active_peers": 8})
        return FakeResp([], 200)

    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV", "password": "PUB"})
        return FakeResp({"status": "ok", "note": "запущен"})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'mn-%'")

    ha.api_session = lambda: FakeSession()
    xray.api_session = lambda: FakeSession()

    print("=== пока на Xray никого — сводка прежняя ===")
    text, markup, _ = await ha.main_menu_view(None, 1)
    line = [l for l in text.split("\n") if "На связи" in l][0]
    print(line)
    assert "AWG" not in line, "лишняя разбивка там, где переезжать некому"

    for uid, name in (("mn-1", "Ника"), ("mn-2", "Папа")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    async def ips():
        return {"mn-1": "10.13.13.6", "mn-2": "10.13.13.7"}
    xray.peer_ip_map = ips
    await xray.issue("mn-1")
    await xray.issue("mn-2")

    from utils import state_data
    state_data["addr_seen"]["10.13.13.134"] = time.time()
    state_data["addr_seen"]["10.13.13.135"] = time.time()

    print("\n=== кто-то переехал — видно, сколько где ===")
    text, markup, _ = await ha.main_menu_view(None, 1)
    line = [l for l in text.split("\n") if "На связи" in l][0]
    print(line)
    assert "AWG 8" in line and "Xray 2" in line, line
    assert "**10**" in line, "людей на Xray узел пиром не считает — их надо прибавить"
    print("сводка складывает оба протокола: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'mn-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
