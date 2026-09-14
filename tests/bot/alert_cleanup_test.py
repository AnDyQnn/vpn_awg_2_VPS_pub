# -*- coding: utf-8 -*-
"""Уборка чата: доходят ли до неё сообщения и уходят ли они в срок.

Смысл затеи — чтобы чат с ботом не превращался в свалку. Механизм есть: алерт
уходит через notify_admin, тот запоминает его номер, а в полночь всё
накопленное удаляется.

Но механизм и работа — разные вещи, и ломается он тихо:
  • сообщение отправлено в обход notify_admin — номер не записан, и в чате оно
    останется навсегда, а заметить это нельзя ничем, кроме глаз;
  • полночь прошла, а список не почистился — тогда назавтра бот попытается
    удалять по второму разу;
  • уборка прошла дважды за ночь и снесла свежие алерты;
  • Telegram отказал (сообщение старше 48 часов или уже удалено руками) —
    остальные всё равно обязаны удалиться.
"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

import monitor                                   # noqa: E402
from database import db                          # noqa: E402

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
    def __init__(self):
        self.next_id = 100
        self.sent = []
        self.deleted = []
        self.refuse = set()

    async def send_message(self, chat_id, text, **kw):
        self.next_id += 1
        self.sent.append((chat_id, self.next_id))
        return FakeMsg(self.next_id)

    async def delete_message(self, chat_id, message_id):
        if message_id in self.refuse:
            raise RuntimeError("message to delete not found")
        self.deleted.append(message_id)


class FakeApp:
    def __init__(self):
        self.bot = FakeBot()


async def stored():
    return [x for x in ((await db.get_setting("admin_alert_msgs")) or "").split(",") if x]


async def run():
    await db.connect()
    await db.set_setting("admin_alert_msgs", "")
    await db.set_setting("last_alert_cleanup", "")

    app = FakeApp()
    monitor.ADMIN_ID = 777

    print("=== алерт запоминается, а не просто уходит ===")
    m1 = await monitor.notify_admin(app, "первый")
    m2 = await monitor.notify_admin(app, "второй")
    check("отправлено", len(app.bot.sent), 2)
    check("запомнено номеров", len(await stored()), 2)
    check("номера те самые", await stored(),
          [str(m1.message_id), str(m2.message_id)])

    print()
    print("=== полночь: всё накопленное уходит из чата ===")
    # Полночь подменяем, а не ждём: цикл смотрит на часы, и это единственное,
    # что мешает проверить его за секунду.
    midnight = datetime(2026, 9, 14, 0, 2)
    monitor.get_moscow_now = lambda: midnight
    task = asyncio.ensure_future(monitor.midnight_alert_cleanup_loop(app))
    await asyncio.sleep(0.4)
    task.cancel()
    check("удалено из чата", sorted(app.bot.deleted),
          sorted([m1.message_id, m2.message_id]))
    check("список очищен", await stored(), [])

    print()
    print("=== второй заход в ту же ночь ничего не трогает ===")
    m3 = await monitor.notify_admin(app, "свежий, уже после уборки")
    app.bot.deleted.clear()
    task = asyncio.ensure_future(monitor.midnight_alert_cleanup_loop(app))
    await asyncio.sleep(0.4)
    task.cancel()
    check("свежий алерт цел", app.bot.deleted, [])
    check("и остался в списке", await stored(), [str(m3.message_id)])

    print()
    print("=== телеграм отказал по одному — остальные всё равно уходят ===")
    await db.set_setting("admin_alert_msgs", "")
    await db.set_setting("last_alert_cleanup", "")
    a = await monitor.notify_admin(app, "а")
    b = await monitor.notify_admin(app, "б")
    c = await monitor.notify_admin(app, "в")
    app.bot.refuse = {b.message_id}       # например, админ удалил его сам
    app.bot.deleted.clear()
    monitor.get_moscow_now = lambda: datetime(2026, 9, 15, 0, 1)
    task = asyncio.ensure_future(monitor.midnight_alert_cleanup_loop(app))
    await asyncio.sleep(0.4)
    task.cancel()
    check("остальные удалены", sorted(app.bot.deleted),
          sorted([a.message_id, c.message_id]))
    check("список всё равно очищен", await stored(), [])

    print()
    print("=== днём уборка не срабатывает ===")
    d = await monitor.notify_admin(app, "дневной")
    app.bot.deleted.clear()
    monitor.get_moscow_now = lambda: datetime(2026, 9, 15, 13, 30)
    task = asyncio.ensure_future(monitor.midnight_alert_cleanup_loop(app))
    await asyncio.sleep(0.4)
    task.cancel()
    check("дневной алерт цел", app.bot.deleted, [])
    check("и ждёт своей полуночи", await stored(), [str(d.message_id)])


asyncio.get_event_loop().run_until_complete(run())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
