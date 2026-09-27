# -*- coding: utf-8 -*-
"""Чистка чатов в конце дня.

Два вопроса. Узнаёт ли она про всё, что бот прислал, — иначе чистить нечего.
И что остаётся после неё: у владельца архивы и главное меню, у человека —
его главное меню. Раньше «экран» определялся как «два последних сообщения», а
экран правится на месте и к ночи уже не последний, — и после уборки в чате не
оставалось ничего, даже закреплённого архива.
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
        deleted.append((chat_id, message_id))

    async def edit_message_text(self, chat_id=None, message_id=None, text=None, **kw):
        edited.append((chat_id, message_id, text))


deleted = []
edited = []


class FakeApp:
    def __init__(self):
        self.bot = FakeBot()
        self.user_data = {}


async def fake_admin_menu(app, chat_id):
    return "ГЛАВНОЕ МЕНЮ ВЛАДЕЛЬЦА", "kb", None


async def fake_user_menu(app, chat_id):
    return "ГЛАВНОЕ МЕНЮ ЧЕЛОВЕКА", "kb", None


async def ids(chat):
    return {r["message_id"] for r in await db.chat_msgs(chat)}


async def main():
    await db.connect()
    await db.execute("DELETE FROM chat_msgs")
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3,$4,$5)",
                     cc.ON_KEY, cc.DONE_KEY, cc.LAST_KEY, "admin_alert_msgs",
                     "backup_message_id")
    cc.admin_menu = fake_admin_menu
    cc.user_menu = fake_user_menu

    # Подменяем то, на что ставится перехват: настоящего telegram.Bot в тесте
    # трогать незачем, а проверяем мы именно механику перехвата.
    cc._patched = False
    assert cc.apply(ADMIN, classes=[FakeBot]), "перехват должен встать"
    assert not cc.apply(ADMIN, classes=[FakeBot]), "второй раз вставать не должен"

    print("=== перехват идёт в тот класс, которым шлёт приложение ===")
    names = [c.__name__ for c in cc._targets()]
    print("  перехватываем:", names)
    assert "ExtBot" in names, names
    ext = [c for c in cc._targets() if c.__name__ == "ExtBot"][0]
    assert "send_message" in ext.__dict__, \
        "ExtBot объявляет send_message сам — значит его и надо перехватывать"
    print("оба класса на месте: ок")

    bot = FakeBot()
    app = FakeApp()

    print("\n=== запоминается всё, и понятно, что это ===")
    screen = await bot.send_message(chat_id=ADMIN, text="меню", reply_markup="kb")
    backup = await bot.send_document(chat_id=ADMIN, document=b"",
                                     caption="💾 **Архив системы · мастер**")
    noise = [await bot.send_message(chat_id=ADMIN, text="тревога"),
             await bot.send_document(chat_id=ADMIN, document=b"", caption="выгрузка"),
             await bot.send_photo(chat_id=ADMIN, photo=b"")]
    kinds = {r["message_id"]: r["kind"] for r in await db.chat_msgs(ADMIN)}
    assert kinds[screen.message_id] == "menu", kinds
    assert kinds[backup.message_id] == "backup", kinds
    assert all(kinds[m.message_id] == "" for m in noise), kinds
    print("  экран — menu, архив — backup, прочее — без пометки: ок")

    print("\n=== ручная уборка: экран и архив остаются, хоть экран и старый ===")
    # Экран отправлен первым, а после него пришло три сообщения. Прежняя
    # уборка «оставляла два последних» — и экран уходил.
    deleted.clear()
    gone = await cc.sweep(app, ADMIN, anchor=screen.message_id)
    left = await ids(ADMIN)
    assert gone == 3, gone
    assert left == {screen.message_id, backup.message_id}, left
    assert (ADMIN, screen.message_id) not in deleted
    print("  убрано %d, остались экран и архив: ок" % gone)

    print("\n=== закреплённый архив прежних версий — по номеру из настроек ===")
    old_backup = await bot.send_document(chat_id=ADMIN, document=b"")   # без подписи
    await db.set_setting("backup_message_id", str(old_backup.message_id))
    await cc.sweep(app, ADMIN, anchor=screen.message_id)
    assert old_backup.message_id in await ids(ADMIN)
    print("  архив по номеру цел: ок")

    print("\n=== ночь: экран владельца становится главным меню ===")
    await bot.send_message(chat_id=ADMIN, text="шум")
    edited.clear()
    # Бот помнит экран так же, как show_screen его запоминает.
    app.user_data[ADMIN] = {"screen_at": (ADMIN, screen.message_id)}
    mine, _, _ = await cc.sweep_all(app, ADMIN)
    assert mine == 1, mine
    assert (ADMIN, screen.message_id, "ГЛАВНОЕ МЕНЮ ВЛАДЕЛЬЦА") in edited, edited
    assert {screen.message_id, backup.message_id, old_backup.message_id} <= await ids(ADMIN)
    print("  шум убран, экран переписан в главное меню, архивы на месте: ок")

    print("\n=== бот перезапускался и экран не помнит — берёт последний с кнопками ===")
    app.user_data.clear()
    await bot.send_message(chat_id=ADMIN, text="шум")
    edited.clear()
    await cc.sweep_all(app, ADMIN)
    assert edited and edited[-1][1] == screen.message_id, edited
    print("  главное меню встало на прежний экран: ок")

    print("\n=== чат человека: остаётся его главное меню ===")
    u_menu = await bot.send_message(chat_id=OTHER, text="меню человека", reply_markup="kb")
    u_conf = await bot.send_document(chat_id=OTHER, document=b"", caption="📄 Ваш VPN конфиг")
    u_note = await bot.send_message(chat_id=OTHER, text="🟢 VPN Подключен")
    deleted.clear(); edited.clear()
    _, theirs, chats = await cc.sweep_all(app, ADMIN)
    assert theirs == 2 and chats == 1, (theirs, chats)
    assert (OTHER, u_conf.message_id) in deleted and (OTHER, u_note.message_id) in deleted
    assert (OTHER, u_menu.message_id, "ГЛАВНОЕ МЕНЮ ЧЕЛОВЕКА") in edited, edited
    assert await ids(OTHER) == {u_menu.message_id}
    print("  копия ключа и шум убраны, меню человека переписано и осталось: ок")

    print("\n=== у человека не было экрана — меню приходит новым, без звука ===")
    await db.execute("DELETE FROM chat_msgs WHERE chat_id=$1", OTHER)
    await bot.send_message(chat_id=OTHER, text="уведомление без кнопок")
    sent = []
    orig = FakeBot.send_message

    async def spy(self, chat_id=None, *a, **kw):
        sent.append((chat_id, kw.get("disable_notification")))
        return await orig(self, chat_id, *a, **kw)
    app.bot.send_message = spy.__get__(app.bot)
    await cc.sweep_all(app, ADMIN)
    assert (OTHER, True) in sent, sent
    print("  новое меню, тихо: ок")

    print("\n=== чужие группы не запоминаются ===")
    await bot.send_message(chat_id=-100500, text="группа")
    assert not await db.chat_msgs(-100500)
    print("  ок")

    print("\n=== старые тревоги из прежнего списка тоже уходят ===")
    deleted.clear()
    await db.set_setting("admin_alert_msgs", "555,556,557")
    await cc.sweep(app, ADMIN, anchor=screen.message_id)
    assert {555, 556, 557} <= {m for _, m in deleted}, deleted
    assert (await db.get_setting("admin_alert_msgs")) == ""
    print("хвост прежней чистки подобран: ок")

    print("\n=== выключенная чистка молчит ===")
    await db.set_setting(cc.ON_KEY, "0")
    assert not await cc.enabled()
    print("тумблер работает: ок")

    await db.execute("DELETE FROM chat_msgs")
    await db.execute("DELETE FROM settings WHERE key IN ($1,$2,$3,$4,$5)",
                     cc.ON_KEY, cc.DONE_KEY, cc.LAST_KEY, "admin_alert_msgs",
                     "backup_message_id")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
