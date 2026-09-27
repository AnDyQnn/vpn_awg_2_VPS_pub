# -*- coding: utf-8 -*-
"""Старый ключ перевыпуска — не призрак.

27.09: перевыпуск ключа Светы, старый пир переименован в `retired-<uuid>` и
должен был держать связь до перехода на новый. Через четыре секунды сторож
не нашёл такого uuid в базе, объявил «призраком», убил, стёр из конфига и
прислал «несанкционированный доступ» — с её же домашним адресом. Перевыпуск
«без обрыва» на деле рвал связь.

Прогоняем настоящего сторожа на одном круге с подставным узлом.
"""
import asyncio

from database import db
import monitor


class Stop(Exception):
    pass


class Resp:
    def __init__(self, payload):
        self._p, self.status = payload, 200

    def raise_for_status(self):
        pass

    async def json(self):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


KILLED = []


class Session:
    def get(self, url, **kw):
        return Resp(PEERS)

    def post(self, url, json=None, **kw):
        if url.endswith("/kill_ghost"):
            KILLED.append(json)
        return Resp({"status": "ok"})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


SENT = []


async def fake_notify(app, text, **kw):
    SENT.append(text)


async def stop_sleep(_):
    raise Stop()


import time  # noqa: E402
NOW = int(time.time())
PEERS = [
    # Света: новый ключ ещё не подключён, старый держит связь.
    {"uuid": "rg-sveta", "public_key": "NEWKEY", "latest_handshake": 0, "endpoint": "(none)"},
    {"uuid": "retired-rg-sveta", "public_key": "OLDKEY", "latest_handshake": NOW - 5,
     "endpoint": "193.0.2.41:55597"},
    # Замороженный человек со старым ключом перевыпуска.
    {"uuid": "retired-rg-paused", "public_key": "PAUSEDOLD", "latest_handshake": NOW - 5,
     "endpoint": "198.51.100.7:4000"},
    # Настоящий призрак: ключ на узле, человека в базе нет.
    {"uuid": "rg-nobody", "public_key": "GHOST", "latest_handshake": NOW - 5,
     "endpoint": "203.0.113.9:5000"},
]


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rg-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Света', 'rg-sveta', TRUE)")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Пауза', 'rg-paused', FALSE)")

    monitor.api_session = lambda: Session()
    monitor.notify_admin = fake_notify
    monitor.asyncio.sleep = stop_sleep
    try:
        await monitor.alert_loop(None)
    except Stop:
        pass

    killed = {k["public_key"]: k for k in KILLED}
    print("  снято:", sorted(killed), "| тревог:", len(SENT))

    assert "OLDKEY" not in killed, "старый ключ перевыпуска убит как призрак"
    assert not any("OLDKEY" in s or "193.0.2.41" in s for s in SENT), \
        "тревога о «несанкционированном доступе» с адреса самого человека"
    print("старый ключ перевыпуска живёт, тревоги нет: ок")

    assert "PAUSEDOLD" in killed and killed["PAUSEDOLD"]["purge_config"], \
        "старым ключом замороженного можно было бы обойти заморозку"
    print("старый ключ замороженного снят совсем: ок")

    assert "GHOST" in killed and killed["GHOST"]["purge_config"]
    assert any("GHOST" in s for s in SENT), "про настоящего призрака обязаны сказать"
    print("настоящий призрак по-прежнему ловится: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'rg-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
