# -*- coding: utf-8 -*-
"""Сводка по инцидентам.

Инциденты собирались исправно, а сказать о них было некому: экран есть, но на
него надо прийти. Ровно та поломка, от которой раздел и заводился — «владелец
узнаёт, только если человек пришёл жаловаться».

Главное, что здесь проверяется, — что сводка не превращается в ленту. Инциденты
идут пачками, и сообщение на каждый случай читать перестанут через день, а
вместе с ним перестанут читать и всё остальное.
"""
import asyncio
from datetime import datetime, timedelta

from database import db
import handlers_hits as hh


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.sent.append(text)


class FakeApp:
    def __init__(self):
        self.bot = FakeBot()


async def add(ts, name, ip, domain, category):
    await db.add_filter_hit(ts, "hn-1" if name else None, name, ip, None,
                            domain, category, "AB12-CD34")


async def main():
    await db.connect()
    await db.execute("DELETE FROM filter_hits")
    for key in (hh.LAST_KEY, hh.AT_KEY, hh.ON_KEY, hh.EVERY_KEY):
        await db.execute("DELETE FROM settings WHERE key=$1", key)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'hn-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
        "Ника", "hn-1")

    import utils
    utils.ADMIN_ID = 111
    hh_admin = utils.ADMIN_ID
    assert hh_admin

    now = datetime.utcnow()
    app = FakeApp()

    print("=== первый запуск не вываливает историю ===")
    # Инциденты могли копиться неделями. Первое сообщение стеной текста —
    # верный способ, чтобы его больше никогда не читали.
    for i in range(5):
        await add(now - timedelta(minutes=i), "Ника", "10.13.13.5",
                  "porn%d.example" % i, "adult")
    sent = await hh.notify_new(app)
    print("  отправлено:", sent, "| сообщений:", len(app.bot.sent))
    assert sent == 0 and not app.bot.sent
    marker = int(await db.get_setting(hh.LAST_KEY))
    assert marker > 0, "точка отсчёта обязана запомниться"
    print("запомнил точку и промолчал: ок")

    print("\n=== новое приходит сводкой, а не строками ===")
    for i in range(4):
        await add(now, "Ника", "10.13.13.5", "casino%d.example" % i, "gambling")
    await add(now, None, "10.13.13.9", "porn.example", "adult")
    sent = await hh.notify_new(app)
    assert sent == 5, sent
    assert len(app.bot.sent) == 1, "на пачку — ОДНО сообщение"
    text = app.bot.sent[0]
    print("  ---")
    for line in text.split(chr(10)):
        print("  " + line)
    print("  ---")
    assert "Ника" in text
    assert "casino0.example" in text
    # Неизвестный ключ тоже виден: по адресу, а не «никто».
    assert "10.13.13.9" in text
    print("одно сообщение на пачку, люди сгруппированы: ок")

    print("\n=== чаще выбранного не пишем ===")
    await add(now, "Ника", "10.13.13.5", "ещё.example", "gambling")
    sent = await hh.notify_new(app)
    print("  отправлено:", sent, "| сообщений всего:", len(app.bot.sent))
    assert sent == 0 and len(app.bot.sent) == 1, "тишина между сводками нарушена"
    print("промежуток соблюдается: ок")

    print("\n=== реклама и трекеры не будят, но считаются ===")
    await db.execute("DELETE FROM settings WHERE key=$1", hh.AT_KEY)
    before = int(await db.get_setting(hh.LAST_KEY))
    for i in range(12):
        await add(now, "Ника", "10.13.13.5", "track%d.example" % i, "ads")
    sent = await hh.notify_new(app)
    print("  отправлено:", sent, "| сообщений всего:", len(app.bot.sent))
    # Одна «шумная» пачка вместе с одним обычным: сообщение уходит, но реклама
    # в нём только числом.
    assert len(app.bot.sent) == 2, "обычный инцидент обязан был разбудить"
    text = app.bot.sent[1]
    assert "ещё.example" in text
    assert "track0.example" not in text, "трекеры не должны попадать в строки"
    assert "12" in text, "но их число обязано быть видно"
    after = int(await db.get_setting(hh.LAST_KEY))
    assert after > before, "отметка должна двигаться и по тихим"
    print("шум не будит, но цифры сходятся: ок")

    print("\n=== только реклама — сообщения нет вовсе ===")
    await db.execute("DELETE FROM settings WHERE key=$1", hh.AT_KEY)
    for i in range(5):
        await add(now, "Ника", "10.13.13.5", "ad%d.example" % i, "ads")
    sent = await hh.notify_new(app)
    assert sent == 0 and len(app.bot.sent) == 2, "будить было нечем"
    print("тихая пачка проходит молча: ок")

    print("\n=== выключенная сводка молчит ===")
    await db.set_setting(hh.ON_KEY, "0")
    await db.execute("DELETE FROM settings WHERE key=$1", hh.AT_KEY)
    await add(now, "Ника", "10.13.13.5", "casino-off.example", "gambling")
    sent = await hh.notify_new(app)
    assert sent == 0 and len(app.bot.sent) == 2
    print("выключено — значит выключено: ок")

    await db.execute("DELETE FROM filter_hits")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'hn-%'")
    for key in (hh.LAST_KEY, hh.AT_KEY, hh.ON_KEY, hh.EVERY_KEY):
        await db.execute("DELETE FROM settings WHERE key=$1", key)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
