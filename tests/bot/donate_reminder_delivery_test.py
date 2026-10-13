# -*- coding: utf-8 -*-
"""Напоминание о поддержке: по таймеру, авторским текстом, и кнопкой «сейчас».

Главное, за что тут платят вниманием:
  • людям уходит РОВНО текст из «Текст обращения», ничего зашитого в код;
  • таймерная рассылка (send_reminders) шлёт только тем, кому пора (раз в N
    дней), и держит дневной лимит;
  • «разослать сейчас» (ignore_gate) шлёт всем и сразу;
  • без реквизитов не шлём никому — просить деньги, не сказав куда, нельзя.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                 # noqa: E402
import donate                           # noqa: E402
import handlers_donate as hd            # noqa: E402

TG = 55500111
SENT = []
MYTEXT = "Мой текст: поддержите, реквизиты за кнопкой. (скобки) *звёздочки*"


class Bot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        datas = [b.callback_data for row in
                 (reply_markup.inline_keyboard if reply_markup else []) for b in row]
        # Авторский текст уходит без parse_mode — иначе скобки и звёздочки
        # Markdown принял бы за разметку и сообщение бы не ушло.
        assert kw.get("parse_mode") in (None,), "авторский текст шлём как есть"
        SENT.append({"to": chat_id, "text": text or "", "buttons": datas})


class App:
    def __init__(self):
        self.bot = Bot()


class Query:
    async def answer(self, *a, **k):
        self.alert = a[0] if a else ""

    async def edit_message_text(self, *a, **k):
        pass


class Upd:
    def __init__(self):
        self.callback_query = Query()


class Ctx:
    def __init__(self, app):
        self.application = app


async def only_me():
    return [TG]


async def main():
    await db.connect()
    await db.execute("DELETE FROM donate_methods WHERE value='DR-TEST'")
    await db.execute("INSERT INTO donate_methods (kind, value) VALUES ('card','DR-TEST')")
    await donate.set_enabled(True)
    await donate.set_reminder(True)
    await db.set_setting("donate_reminder_days", "7")
    await donate.set_text(MYTEXT)
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)
    db.get_all_tg_ids = only_me
    app = App()

    print("=== таймер: уходит АВТОРСКИЙ текст, не зашитый ===")
    SENT.clear()
    n = await hd.send_reminders(app)
    mine = [m for m in SENT if m["to"] == TG]
    assert n == 1 and len(mine) == 1, (n, SENT)
    assert mine[0]["text"] == MYTEXT, mine[0]["text"]
    assert "client_donate" in mine[0]["buttons"]
    assert not hasattr(donate, "REMINDER_TEXT"), "зашитого текста больше нет"
    print("  пришёл мой текст целиком, кнопка на месте: ок")

    print("\n=== таймер держит лимит ===")
    SENT.clear()
    assert await hd.send_reminders(app) == 0
    assert not SENT
    print("  в пределах срока повторно не шлём: ок")

    print("\n=== «разослать сейчас» игнорирует срок ===")
    SENT.clear()

    async def no_menu(*a, **k):
        return None
    hd.donate_menu = no_menu                 # перерисовка меню здесь не проверяется
    u = Upd()
    await hd.donate_send_now(u, Ctx(app))
    assert [m for m in SENT if m["to"] == TG], "кнопка должна слать всем сразу"
    assert "Отправлено" in (getattr(u.callback_query, "alert", "") or "")
    print("  отправилось по кнопке несмотря на недавнее: ок")

    print("\n=== нет реквизитов — не шлём ===")
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM donate_methods WHERE value='DR-TEST'")
    SENT.clear()
    assert await hd.send_reminders(app, ignore_gate=True) == 0
    assert not SENT
    print("  без реквизитов тишина: ок")

    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM settings WHERE key='donate_text'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
