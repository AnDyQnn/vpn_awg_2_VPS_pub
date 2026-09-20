# -*- coding: utf-8 -*-
"""Пара для доступа к зоне: где лежит и куда НЕ попадает.

Проверяется именно второе. Через переменную окружения эта пара оказалась бы в
`docker inspect`, в отладочном выводе и в каждом пересоздании контейнеров —
притом что ни один контейнер ею не пользуется, она нужна только хосту.
"""
import asyncio
import os
import stat

import handlers_pubsub as hps


async def main():
    hps.SECRETS_DIR = "/tmp/vpn-secrets-test"
    hps.ZONE_SECRET = os.path.join(hps.SECRETS_DIR, "regru.conf")
    hps.zone_creds_clear()

    print("=== пока пары нет ===")
    assert not hps.zone_api_on()
    print("ничего не задано: ок")

    print("\n=== пара кладётся файлом ===")
    hps.zone_creds_write("ivan", 'па"роль\\с мусором')
    assert hps.zone_api_on()
    body = open(hps.ZONE_SECRET, encoding="utf-8").read()
    print(" ", body.replace("\n", " · ").strip())
    assert "REGRU_API_USER=ivan" in body
    assert "REGRU_API_PASSWORD=" in body
    print("логин и пароль на месте: ок")

    print("\n=== читать может только владелец ===")
    mode = stat.S_IMODE(os.stat(hps.ZONE_SECRET).st_mode)
    print("  права: %o" % mode)
    # На Windows-хосте прав в юниксовом смысле нет; тест гоняется в контейнере,
    # но пусть проверка не врёт, если кто-то запустит его иначе.
    if os.name == "posix":
        assert mode == 0o600, oct(mode)
        assert not mode & (stat.S_IRGRP | stat.S_IROTH)
    print("только владельцу: ок")

    print("\n=== в окружении её нет и быть не должно ===")
    # Это главное. Всё, что попадает в окружение контейнера, попадает и в
    # `docker inspect`, и в вывод отладки, и в глаза тому, кто туда посмотрит.
    for key in ("REGRU_API_USER", "REGRU_API_PASSWORD"):
        assert key not in os.environ, f"{key} оказался в окружении"
    print("окружение чистое: ок")

    print("\n=== правка не требует перезапуска ===")
    # Косвенно, но по существу: запись идёт подменой файла целиком, и никакой
    # просьбы к демону при этом не кладётся.
    before = set(os.listdir("/volumes/flags")) if os.path.isdir("/volumes/flags") else set()
    hps.zone_creds_write("ivan2", "другой")
    after = set(os.listdir("/volumes/flags")) if os.path.isdir("/volumes/flags") else set()
    assert before == after, "правка пары не должна класть просьб демону"
    assert "REGRU_API_USER=ivan2" in open(hps.ZONE_SECRET, encoding="utf-8").read()
    assert not os.path.exists(hps.ZONE_SECRET + ".tmp"), "времянка должна исчезать"
    print("файл заменён целиком, демона не дёргали: ок")

    print("\n=== снятие убирает насовсем ===")
    hps.zone_creds_clear()
    assert not os.path.exists(hps.ZONE_SECRET)
    assert not hps.zone_api_on()
    print("файла нет: ок")

    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
