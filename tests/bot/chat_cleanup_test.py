# -*- coding: utf-8 -*-
"""Чистка чата владельца в конце дня.

Она была и раньше, но знала только про тревоги: их шлют через один помощник,
который запоминает номер. Всё остальное — биллинг, архивы, выгрузки, выдача
ключей, ответы на нажатия — проходило мимо и оставалось в чате навсегда.

Поэтому главное здесь — не «удаляет ли», а «узнаёт ли про всё».
"""
import asyncio

from database import db
import chat_cleanup as cc

ADMIN = 4242
OTHER = 777


class FakeMessage:
    def __init__(self, mid):
        self.message_id = mid


class FakeBot:
    """Подделка настоящего класса: перехват ставится именно на него."""
    _next = 1000

    async def send_message(self, chat_id=None, *a, **kw):
        FakeBot._next += 1
        return FakeMessage(FakeBot._next)

    async def send_document(self, chat_id=None, *a, **kw):
        FakeBot._next += 1
        return FakeMessage(FakeBot._next)

    async def send_photo(self, chat_id=None, *a, **kw):
        FakeBot._next += 1
        return FakeMessage(FakeBot._next)

    async def delete_message(self, chat_id=None, message_id=None):
        deleted.append(message_id)


deleted = []


class FakeApp:
    def __init__(self):
        self.bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM chat_msgs WHERE chat_id IN ($1,$2)", ADMIN, OTHER)
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3)",
                     cc.ON_KEY, cc.DONE_KEY, "admin_alert_msgs")

    # Подменяем то, на что ставится перехват: настоящего telegram.Bot в тесте
    # трогать незачем, а проверяем мы именно механику перехвата.
    cc._patched = False
    assert cc.apply(ADMIN, classes=[FakeBot]), "перехват должен встать"
    assert not cc.apply(ADMIN, classes=[FakeBot]), "второй раз вставать не должен"

    print("=== перехват идёт в тот класс, которым шлёт приложение ===")
    # Приложение шлёт не голым Bot, а ExtBot, и тот переопределяет
    # send_message. Перехват только на Bot до живого бота не доезжает — и
    # выглядит это как работающая чистка, которой нечего чистить.
    targets = cc._targets()
    names = [c.__name__ for c in targets]
    print("  перехватываем:", names)
    assert "ExtBot" in names, names
    ext = [c for c in targets if c.__name__ == "ExtBot"][0]
    assert "send_message" in ext.__dict__,         "ExtBot объявляет send_message сам — значит его и надо перехватывать"
    print("оба класса на месте: ок")
    print()

    bot = FakeBot()

    print("=== запоминается ВСЁ, что ушло владельцу ===")
    # Три разных способа отправки: текст, документ, картинка. Прежняя чистка
    # знала только про один и только из одного места.
    m1 = await bot.send_message(chat_id=ADMIN, text="тревога")
    m2 = await bot.send_document(chat_id=ADMIN, document=b"")
    m3 = await bot.send_photo(chat_id=ADMIN, photo=b"")
    rows = await db.chat_msgs(ADMIN)
    got = {r["message_id"] for r in rows}
    print("  запомнено:", sorted(got))
    assert {m1.message_id, m2.message_id, m3.message_id} <= got, got
    print("текст, документ и картинка — все три: ок")

    print("\n=== чужой чат не трогаем вовсе ===")
    mo = await bot.send_message(chat_id=OTHER, text="ключ человеку")
    rows = await db.chat_msgs(OTHER)
    assert not rows, "чужие сообщения запоминать нельзя"
    print("  сообщений чужого чата в списке:", len(rows))
    print("человек хранит свой ключ сам: ок")

    print("\n=== последние не трогаем ===")
    rows = await db.chat_msgs(ADMIN, keep_last=cc.KEEP_LAST)
    kept = {r["message_id"] for r in rows}
    print("  под удаление:", sorted(kept))
    assert m3.message_id not in kept, "самое свежее обязано остаться"
    assert m2.message_id not in kept, "и предыдущее тоже"
    assert m1.message_id in kept
    print("экран с кнопками переживает чистку: ок")

    print("\n=== уборка удаляет и забывает ===")
    deleted.clear()
    for _ in range(4):
        await bot.send_message(chat_id=ADMIN, text="шум")
    app = FakeApp()
    gone = await cc.sweep(app, ADMIN)
    print("  убрано:", gone, "| удалено в телеграме:", len(deleted))
    assert gone == len(deleted) > 0
    left = await db.chat_msgs(ADMIN)
    assert len(left) == cc.KEEP_LAST, left
    print("в списке остались только последние: ок")

    print("\n=== старые тревоги из прежнего списка тоже уходят ===")
    # Иначе они остались бы в чате навсегда: прежний список после этой версии
    # никто не пополняет и никто не разбирает.
    deleted.clear()
    await db.set_setting("admin_alert_msgs", "555,556,557")
    gone = await cc.sweep(app, ADMIN)
    print("  удалено:", sorted(deleted))
    assert {555, 556, 557} <= set(deleted), deleted
    assert (await db.get_setting("admin_alert_msgs")) == ""
    print("хвост прежней чистки подобран: ок")

    print("\n=== выключенная чистка молчит ===")
    await db.set_setting(cc.ON_KEY, "0")
    assert not await cc.enabled()
    print("тумблер работает: ок")

    await db.execute("DELETE FROM chat_msgs WHERE chat_id IN ($1,$2)", ADMIN, OTHER)
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3)",
                     cc.ON_KEY, cc.DONE_KEY, "admin_alert_msgs")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
