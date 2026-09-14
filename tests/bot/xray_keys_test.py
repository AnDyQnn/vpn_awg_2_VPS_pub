# -*- coding: utf-8 -*-
"""Разбор ключей Reality переживает переименование полей.

Найдено на бою: Xray 26.3.27 стал печатать «PrivateKey» и «Password
(PublicKey)» вместо прежних «Private key» и «Public key». Разбор искал точные
имена, не нашёл — и весь выпуск ключа отваливался. Владелец нажал кнопку и не
получил ничего: ни ключа, ни внятной причины.

Переименуют ещё — поэтому проверяем не одно конкретное имя, а то, что разбор
держит все виденные виды и честно отказывается на незнакомом.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

import xray                                       # noqa: E402
from database import db                           # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-44s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeResp:
    def __init__(self, payload):
        self._p, self.status = payload, 200

    async def json(self):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    payload = {}

    def post(self, url, **kw):
        return FakeResp(FakeSession.payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def keys_from(payload):
    """Прогоняет выдачу узла через настоящий разбор и возвращает результат."""
    FakeSession.payload = payload
    for key in ("xray_private_key", "xray_public_key", "xray_short_id"):
        await db.set_setting(key, "")
    return await xray.ensure_keys()


async def run():
    await db.connect()
    xray.api_session = lambda: FakeSession()

    print("=== 26.3: PrivateKey / Password (PublicKey) / Hash32 ===")
    got = await keys_from({"privatekey": "прив-новый",
                           "password_(publickey)": "пуб-новый",
                           "hash32": "хеш"})
    check("ключи разобраны", bool(got))
    check("закрытый тот", got and got["private_key"] == "прив-новый", got and got["private_key"])
    check("открытый тот", got and got["public_key"] == "пуб-новый", got and got["public_key"])

    print()
    print("=== старый формат: Private key / Public key ===")
    got = await keys_from({"private_key": "прив-старый", "public_key": "пуб-старый"})
    check("ключи разобраны", bool(got))
    check("закрытый тот", got and got["private_key"] == "прив-старый")
    check("открытый тот", got and got["public_key"] == "пуб-старый")

    print()
    print("=== ещё одно мыслимое переименование ===")
    got = await keys_from({"private-key": "прив-3", "publickey_password": "пуб-3"})
    check("разбор не развалился", bool(got))

    print()
    print("=== незнакомый формат: отказываемся, а не подсовываем мусор ===")
    got = await keys_from({"foo": "1", "bar": "2"})
    check("вернул пустоту", got is None)

    for key in ("xray_private_key", "xray_public_key", "xray_short_id"):
        await db.set_setting(key, "")


asyncio.get_event_loop().run_until_complete(run())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
