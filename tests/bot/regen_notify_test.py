# -*- coding: utf-8 -*-
"""После перевыпуска подключение по новому ключу не проходит молча.

«Новое подключение» владелец получает только при самом первом подключении
человека. Перевыпуск оставляет человека прежним, поэтому переход на новый
ключ был виден лишь в журнале. Теперь о нём приходит сообщение — один раз.
"""
import asyncio

from database import db
import monitor

SENT = []


class Resp:
    status = 200

    def __init__(self, payload):
        self._p = payload

    async def json(self):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class Session:
    def get(self, url, **kw):
        return Resp([{"uuid": "rn-1", "latest_handshake": 1790000000,
                      "endpoint": "95.24.1.2:5555"},
                     {"uuid": "retired-rn-1", "latest_handshake": 1789999000,
                      "endpoint": "95.24.1.2:4444"}])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def fake_notify(app, text=None, **kw):
    SENT.append(text)


async def run_once():
    t = asyncio.ensure_future(monitor.retire_watch_loop(None))
    await asyncio.sleep(0.5)
    t.cancel()


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rn-%'")
    await db.execute("DELETE FROM pending_retire WHERE old_uuid LIKE 'retired-rn-%'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('Перевыпущенный','rn-1')")
    await db.queue_retire("retired-rn-1", "rn-1", "Перевыпущенный")

    monitor.api_session = lambda **k: Session()
    monitor.notify_admin = fake_notify
    monitor.ADMIN_ID = 1

    await run_once()
    msgs = [m for m in SENT if "новому ключу" in (m or "")]
    assert len(msgs) == 1, SENT
    assert "Перевыпущенный" in msgs[0] and "95.24.1.2" in msgs[0], msgs[0]
    print("владелец узнал о подключении по новому ключу: ок")
    print("  ---\n  " + msgs[0].replace("\n", "\n  "))

    await run_once()
    assert len([m for m in SENT if "новому ключу" in (m or "")]) == 1, \
        "сообщение не должно повторяться"
    print("второй проход молчит: ок")

    await db.execute("DELETE FROM pending_retire WHERE old_uuid LIKE 'retired-rn-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rn-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
