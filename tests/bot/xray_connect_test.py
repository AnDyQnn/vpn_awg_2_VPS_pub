# -*- coding: utf-8 -*-
"""Подключение по Xray замечается и объявляется — как у AmneziaWG.

Владелец: «после того как я включил впн в хапп, мне даже в боте не пришло
уведомление о включении ключа, как с амнезией».

Его и не было. У AmneziaWG есть рукопожатие, и по нему бот давно шлёт «Новое
подключение». У Xray рукопожатия нет, и не слал никто: человек включал VPN, всё
работало, а в боте тишина.

Рядом обнаружилось кое-что хуже. Отметка «подключился по Xray» ставилась в
обработчике подписки — то есть когда приложение СКАЧАЛО список серверов.
Скачало не значит подключилось, а по этой отметке владельцу открывается кнопка
«Убрать AmneziaWG». Выходило, что бот предлагал снять рабочий доступ человеку,
который по Xray не передал ещё ни байта: нажми — и он останется без связи вовсе.

Теперь отметку ставит только живой трафик по адресу-двойнику. Он же и повод
сказать вслух.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402
import monitor                                     # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Bot:
    async def send_message(self, chat_id=None, text="", **k):
        sent.append((chat_id, text))
        return type("M", (), {"message_id": 1, "chat_id": chat_id})()

    async def delete_message(self, *a, **k):
        return None


class App:
    bot = Bot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid='xc-1'")
    await db.execute("DELETE FROM user_tg_links WHERE uuid='xc-1'")
    await db.execute("DELETE FROM users WHERE uuid='xc-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Женя','xc-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('xc-1','x-xc','tok-xc-0123456789')")
    await db.link_user_telegram("xc-1", 4242)

    print("=== скачать подписку — это ещё не подключиться ===")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)
    body = await xray.subscription_body("tok-xc-0123456789")
    check("подписка отдана", bool(body), "приложение забрало список серверов")
    rec = await db.get_xray_user("xc-1")
    check("отметки о подключении нет", not rec["first_seen_at"],
          "иначе откроется снятие AmneziaWG тому, кто ещё не доехал")

    print()
    print("=== пошли пакеты — вот теперь подключился ===")
    sent.clear()
    monitor.ADMIN_ID = 777
    xray.online_uuids = lambda: _set({"xc-1"})
    await one_round()

    rec = await db.get_xray_user("xc-1")
    check("отметка поставлена", bool(rec["first_seen_at"]))
    admin = [t for c, t in sent if c == 777]
    person = [t for c, t in sent if c == 4242]
    check("владельцу сказано", admin and "Xray" in admin[0],
          admin[0][:40] if admin else "тишина")
    check("и человеку тоже", person and "подключен" in person[0].lower(),
          person[0][:40] if person else "тишина")
    check("названо имя ключа", any("Женя" in t for t in admin + person))

    print()
    print("=== второй раз о том же не пишем ===")
    sent.clear()
    await one_round()
    check("повторов нет", not sent,
          "иначе каждое переподключение — сообщение")

    print()
    print("=== разовая починка старых отметок ===")
    await db.execute("UPDATE xray_users SET first_seen_at=NOW() WHERE user_uuid='xc-1'")
    await db.set_setting("xray_seen_by_traffic", "")
    n = await monitor.repair_xray_seen()
    rec = await db.get_xray_user("xc-1")
    check("отметка, поставленная скачиванием, снята", not rec["first_seen_at"],
          "снято %s" % n)
    await db.execute("UPDATE xray_users SET first_seen_at=NOW() WHERE user_uuid='xc-1'")
    await monitor.repair_xray_seen()
    rec = await db.get_xray_user("xc-1")
    check("во второй раз не трогает", bool(rec["first_seen_at"]),
          "починка разовая, иначе она стирала бы честные отметки")

    await db.execute("DELETE FROM xray_users WHERE user_uuid='xc-1'")
    await db.execute("DELETE FROM user_tg_links WHERE uuid='xc-1'")
    await db.execute("DELETE FROM users WHERE uuid='xc-1'")
    await db.set_setting("xray_seen_by_traffic", "")


async def one_round():
    """Один проход сторожа. Цикл вокруг него — только сон, его и не зовём."""
    return await monitor.announce_xray_connects(App())


async def _set(v):
    return v


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
