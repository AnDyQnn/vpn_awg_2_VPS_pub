# -*- coding: utf-8 -*-
"""Уборка чата: доходят ли до неё сообщения и уходят ли они в срок.

Смысл затеи — чтобы чат с ботом не превращался в свалку. Механизм был, но знал
только про тревоги: их шлют через один помощник, который запоминал номер. Всё
остальное — биллинг, архивы, выгрузки, выдача ключей, ответы на нажатия — шло
мимо и оставалось навсегда. Теперь номера запоминает перехват отправки, и
поэтому вопрос «а через тот ли путь послали» больше не стоит.

Ломается такое тихо, поэтому проверяем именно тихие случаи:
  • сообщение ушло в обход помощника тревог — оно всё равно обязано попасть
    в уборку;
  • полночь прошла, а список не почистился — тогда назавтра бот попытается
    удалять по второму разу;
  • уборка прошла дважды за ночь и снесла свежее;
  • Telegram отказал (сообщение старше 48 часов или удалено руками) —
    остальные всё равно обязаны уйти;
  • днём уборка не срабатывает вовсе.
"""
import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "/app")

import monitor                                   # noqa: E402
import chat_cleanup as cc                        # noqa: E402
from database import db                          # noqa: E402

ADMIN = 777
ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok = ok and good
    print("  %s %-44s %s" % ("•" if good else "ПРОВАЛ:", name,
                             got if good else "%s, ждали %s" % (got, want)))


class FakeMsg:
    def __init__(self, mid):
        self.message_id = mid


class FakeBot:
    """Считает, что отправлено и что удалено. Отказ телеграма — отдельно."""
    next_id = 100

    def __init__(self):
        self.sent = []
        self.deleted = []
        self.refuse = set()

    async def send_message(self, chat_id, text=None, **kw):
        FakeBot.next_id += 1
        self.sent.append((chat_id, FakeBot.next_id))
        return FakeMsg(FakeBot.next_id)

    async def delete_message(self, chat_id, message_id):
        if message_id in self.refuse:
            raise RuntimeError("message to delete not found")
        self.deleted.append(message_id)


class FakeApp:
    def __init__(self, bot):
        self.bot = bot


async def stored():
    rows = await db.chat_msgs(ADMIN)
    return sorted(r["message_id"] for r in rows)


async def run():
    await db.connect()
    await db.execute("DELETE FROM chat_msgs WHERE chat_id=$1", ADMIN)
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3)",
                     cc.ON_KEY, cc.DONE_KEY, "admin_alert_msgs")

    bot = FakeBot()
    app = FakeApp(bot)
    monitor.ADMIN_ID = ADMIN

    # Уборка забирает всё, кроме нескольких последних, — здесь это только мешает
    # считать, поэтому на время проверки оставляем ноль. Что последние
    # действительно не трогаются, проверяет chat_cleanup_test.
    cc.KEEP_LAST = 0
    cc.START_DELAY = 0.01
    cc.CHECK_SECONDS = 0.01
    cc._patched = False
    cc.apply(ADMIN, classes=[FakeBot])

    print("=== тревога запоминается, а не просто уходит ===")
    m1 = await monitor.notify_admin(app, "первый")
    m2 = await monitor.notify_admin(app, "второй")
    check("отправлено", len(bot.sent), 2)
    check("запомнено номеров", len(await stored()), 2)
    check("номера те самые", await stored(),
          sorted([m1.message_id, m2.message_id]))

    print()
    print("=== то, что послано МИМО помощника тревог, тоже ===")
    # Ровно этого прежняя уборка не умела, и из-за этого её считали сломанной.
    mimo = await bot.send_message(ADMIN, "биллинг, архив, ответ на нажатие")
    check("и оно в списке", mimo.message_id in await stored(), True)

    print()
    print("=== полночь: всё накопленное уходит из чата ===")
    # Полночь подменяем, а не ждём: цикл смотрит на часы, и это единственное,
    # что мешает проверить его за секунду.
    cc.get_moscow_now = lambda: datetime(2026, 9, 14, 0, 2)
    task = asyncio.ensure_future(cc.loop(app, ADMIN))
    await asyncio.sleep(0.4)
    task.cancel()
    check("удалено из чата", sorted(bot.deleted),
          sorted([m1.message_id, m2.message_id, mimo.message_id]))
    check("список очищен", await stored(), [])

    print()
    print("=== второй заход в ту же ночь ничего не трогает ===")
    m3 = await monitor.notify_admin(app, "свежий, уже после уборки")
    bot.deleted.clear()
    task = asyncio.ensure_future(cc.loop(app, ADMIN))
    await asyncio.sleep(0.4)
    task.cancel()
    check("свежая тревога цела", bot.deleted, [])
    check("и осталась в списке", await stored(), [m3.message_id])

    print()
    print("=== телеграм отказал по одному — остальные всё равно уходят ===")
    await db.execute("DELETE FROM chat_msgs WHERE chat_id=$1", ADMIN)
    await db.execute("DELETE FROM settings WHERE key=$1", cc.DONE_KEY)
    a = await monitor.notify_admin(app, "а")
    b = await monitor.notify_admin(app, "б")
    c = await monitor.notify_admin(app, "в")
    bot.refuse = {b.message_id}       # например, владелец удалил его сам
    bot.deleted.clear()
    cc.get_moscow_now = lambda: datetime(2026, 9, 15, 0, 1)
    task = asyncio.ensure_future(cc.loop(app, ADMIN))
    await asyncio.sleep(0.4)
    task.cancel()
    check("остальные удалены", sorted(bot.deleted),
          sorted([a.message_id, c.message_id]))
    check("список всё равно очищен", await stored(), [])

    print()
    print("=== днём уборка не срабатывает ===")
    d = await monitor.notify_admin(app, "дневной")
    bot.deleted.clear()
    cc.get_moscow_now = lambda: datetime(2026, 9, 15, 13, 30)
    task = asyncio.ensure_future(cc.loop(app, ADMIN))
    await asyncio.sleep(0.4)
    task.cancel()
    check("дневная тревога цела", bot.deleted, [])
    check("и ждёт своей полуночи", await stored(), [d.message_id])

    print()
    print("=== выключенная уборка не трогает ничего даже в полночь ===")
    await db.set_setting(cc.ON_KEY, "0")
    await db.execute("DELETE FROM settings WHERE key=$1", cc.DONE_KEY)
    bot.deleted.clear()
    cc.get_moscow_now = lambda: datetime(2026, 9, 16, 0, 1)
    task = asyncio.ensure_future(cc.loop(app, ADMIN))
    await asyncio.sleep(0.4)
    task.cancel()
    check("ничего не удалено", bot.deleted, [])
    check("список цел", await stored(), [d.message_id])

    await db.execute("DELETE FROM chat_msgs WHERE chat_id=$1", ADMIN)
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3)",
                     cc.ON_KEY, cc.DONE_KEY, "admin_alert_msgs")


asyncio.get_event_loop().run_until_complete(run())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
