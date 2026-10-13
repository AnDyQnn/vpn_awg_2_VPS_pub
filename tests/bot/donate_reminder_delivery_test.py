# -*- coding: utf-8 -*-
"""Напоминание о поддержке доходит и до тех, кто список изменений уже видел.

Оно рассылается хвостом к «Что нового». Раньше стояло внутри ветки «есть
непрочитанное» и после continue — поэтому человек, уже открывавший «Что
нового», напоминания не получал вовсе, а это большинство. Проверяем, что
теперь получает, и что дневной лимит по-прежнему держит.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db          # noqa: E402
import changelog                 # noqa: E402
import donate                    # noqa: E402
import bot as B                  # noqa: E402

TG = 55500111
SENT = []


class Bot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        datas = [b.callback_data for row in
                 (reply_markup.inline_keyboard if reply_markup else []) for b in row]
        SENT.append({"to": chat_id, "text": text or "", "buttons": datas})


class App:
    def __init__(self):
        self.bot = Bot()


async def only_me():
    return [TG]


async def main():
    await db.connect()
    # Обстановка: донат включён, реквизит есть, напоминание включено, раз в 7 дн.
    await db.execute("DELETE FROM donate_methods WHERE value='DR-TEST'")
    await db.execute("INSERT INTO donate_methods (kind, value) VALUES ('card','DR-TEST')")
    await donate.set_enabled(True)
    await donate.set_reminder(True)
    await db.set_setting("donate_reminder_days", "7")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)

    # Подменяем окружение рассылки: только наш tg, и человек «всё уже видел».
    changelog.user_text = lambda since_version=None: ""
    changelog.fit = lambda s, n=3500: s
    db.get_all_tg_ids = only_me

    print("=== человек без непрочитанного — напоминание всё равно пришло ===")
    SENT.clear()
    await B.notify_users_whats_new(App())
    rem = [m for m in SENT if m["to"] == TG]
    assert len(rem) == 1, SENT
    assert donate.REMINDER_TEXT[:20] in rem[0]["text"], rem[0]["text"]
    assert "client_donate" in rem[0]["buttons"], rem[0]
    assert not await donate.should_remind(TG), "отметка о напоминании должна встать"
    print("  «Что нового» пусто, а напоминание ушло и отметилось: ок")

    print("\n=== второй проход подряд — молчит (дневной лимит) ===")
    SENT.clear()
    await B.notify_users_whats_new(App())
    assert not [m for m in SENT if m["to"] == TG], SENT
    print("  повтор подавлен: ок")

    print("\n=== есть непрочитанное — и список, и напоминание ===")
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)   # как будто давно не напоминали
    changelog.user_text = lambda since_version=None: "• что-то новое"
    SENT.clear()
    await B.notify_users_whats_new(App())
    mine = [m for m in SENT if m["to"] == TG]
    assert any("что-то новое" in m["text"] for m in mine), mine
    assert any("client_donate" in m["buttons"] for m in mine), mine
    print("  пришли оба сообщения: ок")

    print("\n=== реквизитов нет — напоминания нет ===")
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM donate_methods WHERE value='DR-TEST'")
    changelog.user_text = lambda since_version=None: ""
    SENT.clear()
    await B.notify_users_whats_new(App())
    assert not [m for m in SENT if m["to"] == TG], "без реквизитов просить нечем"
    print("  пусто — и правильно: ок")

    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM notify_prefs WHERE tg_id=$1", TG)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
