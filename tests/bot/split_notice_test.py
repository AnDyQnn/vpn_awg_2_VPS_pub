# -*- coding: utf-8 -*-
"""Изменился список исключений — каждому по его случаю.

У AmneziaWG сплит запечён в конфиге: чтобы новые исключения заработали, ключ
нужно перевыпустить. У Xray сплит живёт в профиле маршрутизации, и перевыпуск
его случая не касается вовсе — он выдаёт новую ссылку, а профиль остаётся
прежним.

Рассылка была одна на всех и советовала перевыпуск. Человек на Xray делал, что
сказано, и ничего не менялось.

Проверяется: кому что уходит, и что человек на Xray получает готовый кусок с
профилем, а не совет.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import monitor                                     # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Bot:
    async def send_message(self, chat_id=None, text=None, entities=None, **kw):
        sent.append({"to": chat_id, "text": text or "", "code": bool(entities)})


class App:
    bot = Bot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sn-%'")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id IN (5551, 5552)")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sn-%'")

    version = await db.get_routing_version()
    # Оба отстали от текущей версии маршрутизации: именно их и собирает рассылка.
    await db.execute(
        "INSERT INTO users (name, uuid, is_active, routing_version) "
        "VALUES ('Иксрейщик','sn-1',TRUE,$1)", max(0, version - 1))
    await db.execute(
        "INSERT INTO users (name, uuid, is_active, routing_version) "
        "VALUES ('Амнезиевич','sn-2',TRUE,$1)", max(0, version - 1))
    await db.execute("INSERT INTO user_tg_links (uuid, tg_id) VALUES ('sn-1',5551)")
    await db.execute("INSERT INTO user_tg_links (uuid, tg_id) VALUES ('sn-2',5552)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('sn-1','x-sn','tok-sn')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    await monitor._send_upgrade_notices(App())

    to_xray = [m for m in sent if m["to"] == 5551]
    to_awg = [m for m in sent if m["to"] == 5552]

    print("=== человеку на Xray ===")
    check("что-то пришло", bool(to_xray), "сообщений: %d" % len(to_xray))
    joined = "\n".join(m["text"] for m in to_xray)
    check("сказано, что список изменился", "исключени" in joined.lower())
    check("прислан готовый кусок", "vless://" in joined and "happ://routing/" in joined,
          "перевыпуск его случая не касается")
    check("кусок отдан кодом", any(m["code"] for m in to_xray),
          "нажал — скопировалось")
    check("перевыпуск не предлагается", "еревыпуст" not in joined,
          "он выдаёт новую ссылку, а профиль остаётся прежним")

    print()
    print("=== человеку на AmneziaWG ===")
    joined_awg = "\n".join(m["text"] for m in to_awg)
    check("что-то пришло", bool(to_awg), "сообщений: %d" % len(to_awg))
    check("ему как раз про перевыпуск", "еревыпуст" in joined_awg,
          "у него сплит запечён в конфиге")
    check("куска с профилем нет", "happ://routing/" not in joined_awg)

    print()
    print("=== повторная рассылка не дублирует ===")
    row = await db.fetch_all(
        "SELECT routing_version FROM users WHERE uuid='sn-1'")
    check("версия у него обновилась",
          row and row[0]["routing_version"] == version,
          "иначе он получал бы тот же кусок каждый час")

    sent.clear()
    await monitor._send_upgrade_notices(App())
    check("второй раз ему ничего не ушло",
          not [m for m in sent if m["to"] == 5551], str(len(sent)))

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'sn-%'")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id IN (5551, 5552)")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sn-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
