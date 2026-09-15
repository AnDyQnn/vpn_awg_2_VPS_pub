# -*- coding: utf-8 -*-
"""Что человек получает на руки.

Смысл подписки в том, что вставляют ОДНО. Пока она была закрыта, отдать её
адрес было нельзя: чтобы его прочитать, надо уже быть подключённым, а человек
как раз ещё не подключён, — поэтому уходили сами сервера и профиль
маршрутизации отдельной строкой. Это работало, но каждое изменение списка
исключений снова собирало всех.

Теперь, когда снаружи отвечают, уходит один адрес, и приложение забирает по
нему всё остальное само.

Проверяется ровно эта развилка — и то, что закрытая подписка не превращает
выдачу в нерабочий адрес, по которому никто не ответит.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402
import handlers_pubsub                             # noqa: E402
import handlers_xray                               # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'ha-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ha-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Ктотам','ha-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('ha-1','x-ha','tok-ha-0123456789')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)
    # Своего адреса подписки владелец не задавал — как на живом узле.
    await db.set_setting("xray_sub_base", "")

    print("=== подписка закрыта ===")
    handlers_pubsub.CERT_FILE = "/nonexistent/fullchain.pem"
    handlers_pubsub.STATE_FILE = "/nonexistent/public_sub.json"
    check("состояние закрыто", not handlers_pubsub.is_on())
    check("адрес подписки не отдаётся",
          await xray.public_sub_url("ha-1") == "",
          "снаружи по нему никто не ответит")

    lines = await xray.bundle_lines("ha-1")
    check("уходят сами сервера", any(l.startswith("vless://") for l in lines),
          "строк: %d" % len(lines))
    check("и профиль маршрутизации последней строкой",
          any(l.startswith("happ://routing/") for l in lines))

    text = await handlers_xray.instructions("ha-1")
    check("про самообновление не обещаем",
          "подтянет само" not in text,
          "обещание, которого не будет, хуже молчания")

    print()
    print("=== подписка открыта ===")
    cert_dir = "/tmp/hacert"
    os.makedirs(cert_dir, exist_ok=True)
    open(os.path.join(cert_dir, "fullchain.pem"), "w").write("x")
    state = os.path.join(cert_dir, "public_sub.json")
    open(state, "w").write(
        '{"state":"on","msg":"ok","port":8443,"at":1,"until":9999999999,'
        '"ip":"203.0.113.10"}')
    handlers_pubsub.CERT_FILE = os.path.join(cert_dir, "fullchain.pem")
    handlers_pubsub.STATE_FILE = state
    check("состояние открыто", handlers_pubsub.is_on())

    url = await xray.public_sub_url("ha-1")
    check("адрес личный и по https", url.startswith("https://203.0.113.10:8443/sub/"),
          url)
    check("в нём личный токен", url.endswith("tok-ha-0123456789"), url)

    lines = await xray.bundle_lines("ha-1")
    check("уходит РОВНО одна строка", len(lines) == 1, "строк: %d" % len(lines))
    check("и это адрес подписки", lines and lines[0] == url)
    check("серверов россыпью больше нет",
          not any(l.startswith("vless://") for l in lines),
          "вставлять человек должен одно, а не разбираться в четырёх строках")

    text = await handlers_xray.instructions("ha-1")
    check("сказано, что дальше само", "подтянет само" in text,
          "иначе он будет ждать сообщения, которого не будет")

    print()
    print("=== адрес меняется вместе с состоянием, без настроек ===")
    os.remove(os.path.join(cert_dir, "fullchain.pem"))
    check("сертификат убрали — адрес не отдаётся",
          await xray.public_sub_url("ha-1") == "")
    lines = await xray.bundle_lines("ha-1")
    check("выдача вернулась к серверам",
          any(l.startswith("vless://") for l in lines),
          "закрытая подписка не должна оставлять человека с мёртвым адресом")

    print()
    print("=== чужому ключу чужого не достаётся ===")
    check("без выданного Xray адреса нет",
          await xray.public_sub_url("ha-нет-такого") == "")

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'ha-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ha-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
