# -*- coding: utf-8 -*-
"""Экран группы отдаёт список так, чтобы его можно было скопировать.

Список — одним блоком кода: в Telegram он копируется целиком одним нажатием.
Раньше показывались первые двенадцать адресов по одному, и чтобы передать
список другому владельцу, его приходилось перепечатывать. Длинный список в
сообщение не влезает (предел Telegram — 4096 знаков) — тогда он приходит
файлом по кнопке.
"""
import asyncio

from database import db
import filters


class Msg:
    chat_id = 4242
    message_id = 1
    photo = None
    document = None


class Query:
    def __init__(self):
        self.message = Msg()
        self.text = None
        self.kb = None

    async def edit_message_text(self, text, reply_markup=None, **kw):
        self.text, self.kb = text, reply_markup

    async def answer(self, *a, **k):
        pass


class Bot:
    def __init__(self):
        self.docs = []

    async def send_document(self, chat_id=None, document=None, caption=None, **kw):
        self.docs.append((document.name, document.getvalue().decode(), caption))


class Ctx:
    def __init__(self):
        self.user_data = {}
        self.bot = Bot()


class Upd:
    def __init__(self):
        self.callback_query = Query()


def buttons(q):
    return [b.callback_data for row in q.kb.inline_keyboard for b in row]


async def main():
    await db.connect()
    small = ["likee.video", "like.video", "like-video.com", "likee.com"]
    big = ["host%04d.example-long-domain.test" % i for i in range(400)]
    await db.save_filter_pool("pool_tsmall_aa11", "Маленькая", small)
    await db.save_filter_pool("pool_tbig_bb22", "Большая", big)

    print("=== короткий список — целиком, одним блоком кода ===")
    u, c = Upd(), Ctx()
    await filters.pool_open(u, c, "pool_tsmall_aa11")
    t = u.callback_query.text
    assert "```\n" + "\n".join(small) + "\n```" in t, t
    assert "flt_pool_f_pool_tsmall_aa11" not in buttons(u.callback_query)
    assert len(t) < 4096
    print("  все %d адреса в блоке, кнопки файла нет: ок" % len(small))

    print("\n=== длинный список — сколько влезает, остальное файлом ===")
    u, c = Upd(), Ctx()
    await filters.pool_open(u, c, "pool_tbig_bb22")
    t = u.callback_query.text
    assert len(t) < 4096, len(t)
    assert t.count("```") == 2 and "…и ещё" in t, t[-300:]
    assert "flt_pool_f_pool_tbig_bb22" in buttons(u.callback_query)
    print("  сообщение %d знаков из 4096, есть кнопка файла: ок" % len(t))

    await filters.pool_file(u, c, "pool_tbig_bb22")
    name, body, caption = c.bot.docs[-1]
    assert body.split() == big and name == "tbig_bb22.txt", (name, body[:80])
    assert "400" in caption
    print("  файл %s — все %d адресов: ок" % (name, len(big)))

    for k in ("pool_tsmall_aa11", "pool_tbig_bb22"):
        await db.delete_filter_pool(k)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
