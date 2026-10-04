# -*- coding: utf-8 -*-
"""Человек узнаёт о своей блокировке в боте — с номером, как на странице.

Границы, которые тут и проверяются:
  • мягкий контроль (watch) человеку не доходит никогда — это функция владельца;
  • владельцу его же ключи вторым сообщением не шлём (у него сводка);
  • один сайт не спамит — тихое окно на пару «ключ+домен»;
  • реклама и трекеры человеку не показываются;
  • на его экране инцидентов — только его ключи и только запреты.
"""
import asyncio
import time
from datetime import datetime, timedelta

from database import db
import handlers_hits as H
import utils

ADMIN = 100
USER = 200
OWNER_UUID = "ui-own"          # ключ человека
ADMIN_UUID = "ui-adm"          # ключ, привязанный только к владельцу
SENT = []


class Bot:
    async def send_message(self, chat_id=None, text=None, **kw):
        SENT.append((chat_id, text))


class App:
    def __init__(self):
        self.bot = Bot()


async def mkhit(uuid, name, domain, cat, ref, watch=False, ago=0):
    await db.add_filter_hit(datetime.utcnow() - timedelta(seconds=ago),
                            uuid, name, "10.13.13.50", None, domain, cat, ref, watch)


async def main():
    utils.ADMIN_ID = ADMIN
    await db.connect()
    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'ui-%'")
    await db.execute("DELETE FROM user_tg_links WHERE uuid LIKE 'ui-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ui-%'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('Человек',$1), ('МойКлюч',$2)",
                     OWNER_UUID, ADMIN_UUID)
    await db.link_user_telegram(OWNER_UUID, USER)
    await db.link_user_telegram(ADMIN_UUID, ADMIN)     # ключ только у владельца

    app = App()
    # База уже что-то знает: иначе «точка» первого прохода была бы нулевой.
    await mkhit(OWNER_UUID, "Человек", "ui-base.example", "drugs", "BASE", ago=30)
    # Первый проход ставит точку и ничего не шлёт.
    await db.execute("DELETE FROM settings WHERE key=$1", H.USER_LAST_KEY)
    H._user_quiet.clear()
    await H.notify_users(app)
    base = int(await db.get_setting(H.USER_LAST_KEY))
    print("первый проход: точка поставлена на", base, ", сообщений", len(SENT))
    assert not SENT and base > 0

    print("\n=== запрет у человека — приходит с номером и кнопками ===")
    await mkhit(OWNER_UUID, "Человек", "ui-porn.example", "adult", "AA11-BB22")
    await mkhit(ADMIN_UUID, "МойКлюч", "ui-casino.example", "gambling", "CC33")
    # мягкий контроль и реклама — не должны дойти
    await mkhit(OWNER_UUID, "Человек", "ui-watch.example", "social", "WW00", watch=True)
    await mkhit(OWNER_UUID, "Человек", "ui-ad.example", "ads", "AD00")
    SENT.clear()
    await H.notify_users(app)
    to_user = [m for m in SENT if m[0] == USER]
    to_admin = [m for m in SENT if m[0] == ADMIN]
    assert len(to_user) == 1, SENT
    txt = to_user[0][1]
    assert "ui-porn.example" in txt and "AA11-BB22" in txt and "Для взрослых" in txt, txt
    assert "ui-watch" not in txt and "ui-ad.example" not in txt, "мягкий/реклама просочились"
    print("  человек получил свой запрет с номером; watch и реклама — нет: ок")
    assert not to_admin, "владельцу его же ключ вторым сообщением не шлём"
    print("  владельцу дубля по его ключу нет: ок")

    print("\n=== тот же сайт второй раз подряд не спамит ===")
    await mkhit(OWNER_UUID, "Человек", "ui-porn.example", "adult", "AA11-BB23", ago=0)
    SENT.clear()
    await H.notify_users(app)
    assert not [m for m in SENT if m[0] == USER], "сработало тихое окно"
    print("  повтор в пределах окна подавлен: ок")

    print("\n=== кнопки сообщения ===")
    kb = H._user_kb().inline_keyboard
    datas = {b.callback_data for row in kb for b in row}
    assert {"support_start", "myhits", "client_menu"} <= datas, datas
    print("  поддержка, мои инциденты, личный кабинет: ок")

    print("\n=== личный экран: только свои запреты ===")
    class Q:
        def __init__(self):
            self.message = type("M", (), {"chat_id": USER, "message_id": 1,
                                          "photo": None, "document": None})()
            self.text = None

        async def edit_message_text(self, text, **kw):
            self.text = text

        async def answer(self, *a, **k):
            pass

    class Upd:
        def __init__(self):
            self.callback_query = Q()
            self.effective_user = type("U", (), {"id": USER})()
            self.effective_chat = type("C", (), {"id": USER})()

    class Ctx:
        def __init__(self):
            self.user_data = {}

    u = Upd()

    async def fake_screen(q, c, t, **k):
        q.text = t
    H.show_screen = fake_screen
    await H.client_hits_screen(u, Ctx())
    scr = u.callback_query.text
    assert "ui-porn.example" in scr and "AA11-BB22" in scr, scr
    assert "ui-watch" not in scr and "ui-ad.example" not in scr, "лишнее на экране"
    assert "ui-casino" not in scr, "чужой ключ на экране человека"
    print("  видит свой запрет, не видит watch, рекламу и чужое: ок")

    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'ui-%'")
    await db.execute("DELETE FROM user_tg_links WHERE uuid LIKE 'ui-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ui-%'")
    await db.execute("DELETE FROM settings WHERE key=$1", H.USER_LAST_KEY)
    print("\nВСЁ ПРОШЛО")




asyncio.run(main())
