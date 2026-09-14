# -*- coding: utf-8 -*-
"""Отрисовка клиентских экранов на заглушках Telegram. В прод не уезжает."""
import asyncio
from datetime import datetime, timedelta

from database import db
import handlers_client as hc


class Query:
    def __init__(self):
        self.text = None
        self.kb = None
        self.alerts = []

    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        self.text = text
        self.kb = reply_markup

    async def answer(self, text=None, **kw):
        self.alerts.append(text)


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **kw):
        self.sent.append(text)


class Ctx:
    def __init__(self):
        self.bot = Bot()
        self.user_data = {}


class User:
    def __init__(self, uid, name):
        self.id = uid
        self.first_name = name


class Upd:
    def __init__(self, uid, name="Брат"):
        self.effective_user = User(uid, name)
        self.callback_query = Query()

    @property
    def effective_chat(self):
        return self.effective_user


TG = 9001


async def show(title, coro_factory):
    upd, ctx = Upd(TG), Ctx()
    await coro_factory(upd, ctx)
    body = upd.callback_query.text or (ctx.bot.sent[-1] if ctx.bot.sent else "")
    print(f"\n=== {title} ===")
    print(body)
    if upd.callback_query.kb:
        rows = [" | ".join(b.text for b in row)
                for row in upd.callback_query.kb.inline_keyboard]
        print("--- кнопки ---")
        for r in rows:
            print("  " + r)
    return body


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cm-%'")

    soon = datetime.utcnow() + timedelta(days=3)
    far = datetime.utcnow() + timedelta(days=200)
    await db.execute("INSERT INTO users (name, uuid, expires_at) VALUES ('Телефон','cm-1',$1)", soon)
    await db.execute("INSERT INTO users (name, uuid, expires_at) VALUES ('Ноутбук','cm-2',$1)", far)
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Планшет','cm-3',FALSE)")
    for u in ("cm-1", "cm-2", "cm-3"):
        await db.link_user_telegram(u, TG)

    await db.add_pending_decision("cm-3", "dormant", datetime.utcnow() - timedelta(days=40))
    await db.set_peer_limit("cm-1", "custom", 4000)
    await db.execute(
        "INSERT INTO pps_events (user_uuid, started_at, peak_pps, avg_packet_size) "
        "VALUES ('cm-1', NOW() - INTERVAL '3 hours', 6200, 320)")
    await db.execute(
        "INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out) "
        "VALUES ('cm-1', date_trunc('hour', NOW()), 900000000, 350000000)")

    # режим наблюдения: про ограничение не пишем вовсе
    await db.set_setting("pps_mode", "observe")
    body = await show("Главный экран · режим наблюдения", hc.client_menu)
    assert "Ограничение" not in body, "в наблюдении обещать ограничение нельзя"
    assert "Ключей: **3**" in body
    assert "на паузе" in body and "владелец решает" in body
    assert "через 3 дн." in body and "Само ничего не пропадёт" in body

    # режим ограничения: строка появляется
    await db.set_setting("pps_mode", "enforce")
    body = await show("Главный экран · ограничение включено", hc.client_menu)
    assert "ваш предел — 4000" in body, body
    assert "упирались 1 раз" in body, body

    body = await show("Мои ключи", hc.client_my_keys_handler)
    assert "Телефон" in body and "Ноутбук" in body and "Планшет" in body
    assert "🟡" in body and "⏸" in body

    body = await show("Карточка активного ключа",
                      lambda u, c: hc.client_key_manage_handler(u, c, "cm-1"))
    assert "Не подключён" in body
    assert "осталось" in body
    assert "ваш предел — 4000" in body and "упирались 1 раз" in body
    assert "1.2 ГБ" in body, body

    body = await show("Карточка ключа на паузе",
                      lambda u, c: hc.client_key_manage_handler(u, c, "cm-3"))
    assert "На паузе" in body and "не удалён" in body

    # у клиента не должно быть ни слова про роли и доставку — это кухня админа
    await db.execute("INSERT INTO roles (name) VALUES ('Домашние сервисы') "
                     "ON CONFLICT DO NOTHING")
    rid = await db.fetch_val("SELECT id FROM roles WHERE name='Домашние сервисы'")
    await db.add_user_role("cm-1", rid)
    await db.delivery_sent("cm-1", TG)
    for title, factory in (("главный", hc.client_menu),
                           ("список", hc.client_my_keys_handler),
                           ("карточка", lambda u, c: hc.client_key_manage_handler(u, c, "cm-1"))):
        upd, ctx = Upd(TG), Ctx()
        await factory(upd, ctx)
        body = upd.callback_query.text or ctx.bot.sent[-1]
        for word in ("роль", "Роли", "Доставка", "доставк"):
            assert word not in body, f"{title}: клиенту показали «{word}»"
    print("\nролей и доставки в клиентских экранах нет: ок")

    # нажатие кнопки отмечает стадию доставки
    rec = await db.get_delivery("cm-1")
    assert rec["opened_at"], "открытие меню должно отмечать доставку"
    print("открытие меню отмечает доставку: ок")

    await db.execute("DELETE FROM roles WHERE name='Домашние сервисы'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cm-%'")
    await db.execute("DELETE FROM settings WHERE key='pps_mode'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
