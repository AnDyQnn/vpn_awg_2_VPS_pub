# -*- coding: utf-8 -*-
"""Перевыпуск меняет ключ, но не адрес подписки.

Владелец перевыпустил себе доступ — и остался без связи. Причина оказалась в
том, что перевыпуск менял ВСЁ сразу: и ключ, и адрес подписки.

Дальше происходило следующее. Адрес, уже вставленный в приложение, умирал —
по нему приходил 404. Приложение молча оставалось с прежним списком серверов,
а ключ в них был уже отозван. Снаружи это выглядит как «перевыпустил, и ничего
не работает», и починить можно было только вставив новый адрес руками.

То есть подписка переставала быть подпиской ровно в тот момент, когда она
нужнее всего.

Теперь адрес постоянный: приложение забирает по нему новый ключ само.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402
import subscription as S                           # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Req:
    def __init__(self, token):
        self.match_info = {"token": token}
        self.headers = {"Accept": "*/*"}
        self.remote = "203.0.113.90"
        self.url = "https://node/sub/" + token


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid='rk-1'")
    await db.execute("DELETE FROM users WHERE uuid='rk-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Перевыпускин','rk-1',TRUE)")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    # Узел в тестах не отвечает, и apply_config вернёт неудачу — нам это не
    # мешает: проверяем, что записано в базе, а не поднялся ли Xray.
    await xray.issue("rk-1")
    first = await db.get_xray_user("rk-1")
    check("подключение выдано", bool(first))
    addr1 = await xray.subscription_url(first["sub_token"])

    print("=== перевыпуск ===")
    await xray.issue("rk-1")
    second = await db.get_xray_user("rk-1")
    addr2 = await xray.subscription_url(second["sub_token"])

    check("ключ доступа сменился",
          first["xray_uuid"] != second["xray_uuid"],
          "иначе утёкший ключ остался бы рабочим")
    check("адрес подписки ТОТ ЖЕ",
          first["sub_token"] == second["sub_token"],
          "он уже вставлен в приложение — менять его значит рвать связь")
    check("и ссылка та же", addr1 == addr2, addr2)

    print()
    print("=== по старому адресу приходит новый ключ ===")
    resp = await S.handle_sub(Req(first["sub_token"]))
    check("адрес жив", resp.status == 200, "код %s" % resp.status)
    import base64
    body = base64.b64decode(resp.body).decode("utf-8", "replace")
    check("в нём новый ключ", second["xray_uuid"] in body)
    check("старого ключа нет", first["xray_uuid"] not in body,
          "иначе человек подключался бы отозванным")

    print()
    print("=== приложение узнаёт об этом быстро ===")
    check("перечитывать предлагается не реже чем раз в 3 часа",
          S.UPDATE_INTERVAL_HOURS <= 3,
          "сейчас %d ч; перевыпуск отзывает ключ сразу, и до опроса "
          "человек без связи" % S.UPDATE_INTERVAL_HOURS)

    print()
    print("=== адрес можно сменить, но только осознанно ===")
    # Отдельный случай: утёк сам адрес подписки, а не ключ. Тогда новый адрес
    # человеку придётся вставить заново — и просить об этом надо намеренно.
    await xray.issue("rk-1", new_address=True)
    third = await db.get_xray_user("rk-1")
    check("по просьбе адрес меняется",
          third["sub_token"] != second["sub_token"])
    old = await S.handle_sub(Req(second["sub_token"]))
    check("прежний адрес после этого мёртв", old.status == 404,
          "код %s" % old.status)

    await db.execute("DELETE FROM xray_users WHERE user_uuid='rk-1'")
    await db.execute("DELETE FROM users WHERE uuid='rk-1'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
