# -*- coding: utf-8 -*-
"""Перевыпуск ключа на паузе: честный отказ, а не нерабочий конфиг."""
import asyncio
import sys

sys.path.append("/app")
from database import db                       # noqa: E402
import handlers_client as hc                  # noqa: E402

TG = 900000778


class Msg:
    message_id = 1
    chat_id = TG


class Query:
    def __init__(self):
        self.message = Msg()
        self.text = None
        self.kb = None

    async def answer(self, *a, **k):
        pass

    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        self.text, self.kb = text, reply_markup


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.sent.append(text)


class User:
    id = TG
    first_name = "Тест"


class Upd:
    def __init__(self):
        self.callback_query = Query()
        self.effective_user = User()


class Ctx:
    def __init__(self):
        self.bot = Bot()
        self.user_data = {}


async def main():
    await db.connect()
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'pr-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('pr-Пауза','pr-1',FALSE)")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('pr-Рабочий','pr-2')")
    await db.link_user_telegram("pr-1", TG)
    await db.link_user_telegram("pr-2", TG)

    issued = []

    async def fake_issue(context, chat_id, user):
        issued.append(user["uuid"])
        return ("retired-" + user["uuid"], user["name"])

    async def fake_queue(items):
        pass

    hc._issue_new_config = fake_issue
    hc._queue_retire = fake_queue
    try:
        upd, ctx = Upd(), Ctx()
        await hc.client_regen_confirm(upd, ctx, "pr-1")
        assert "на паузе" in upd.callback_query.text, upd.callback_query.text
        print("подтверждение на паузе — отказ с причиной: ок")

        upd, ctx = Upd(), Ctx()
        await hc.client_regen_action(upd, ctx, "pr-1")
        assert not issued and "на паузе" in upd.callback_query.text
        print("перевыпуск на паузе — конфиг не выдан: ок")

        upd, ctx = Upd(), Ctx()
        await hc.client_regen_confirm(upd, ctx, "pr-2")
        assert "Смена ключа" in upd.callback_query.text
        print("рабочий ключ — обычное подтверждение: ок")

        upd, ctx = Upd(), Ctx()
        await hc.client_regen_all_action_handler(upd, ctx)
        assert issued == ["pr-2"], issued
        assert any("на паузе" in (t or "") for t in ctx.bot.sent), ctx.bot.sent
        print("массовый перевыпуск — паузу пропустил и сказал об этом: ок")
    finally:
        await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
        await db.execute("DELETE FROM users WHERE uuid LIKE 'pr-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
