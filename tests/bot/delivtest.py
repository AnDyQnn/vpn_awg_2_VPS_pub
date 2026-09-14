# -*- coding: utf-8 -*-
"""Проверка стадий доставки ключа. В прод не уезжает."""
import asyncio
from datetime import datetime, timedelta

from database import db
import delivery


async def main():
    await db.connect()
    print("подключение и миграции: ок")

    exists = await db.fetch_val(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='key_delivery'")
    assert exists
    print("  таблица key_delivery: есть")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'dl-%'")
    for uid, name in (("dl-1", "Дошёл"), ("dl-2", "Молчун"),
                      ("dl-3", "Заблокировал"), ("dl-4", "Скачал")):
        await db.execute("INSERT INTO users (name, uuid) VALUES ($1,$2)", name, uid)

    # ничего не отправляли
    assert await db.get_delivery("dl-1") is None
    assert delivery.stage(None) == ("—", "не отправляли")
    assert "не отправляли" in delivery.describe(None)
    print("ключ без отправки: ок")

    # отправили
    await db.delivery_sent("dl-1", 111)
    rec = await db.get_delivery("dl-1")
    assert rec["sent_at"] and rec["tg_id"] == 111
    assert delivery.stage(rec)[1] == "отправлено, реакции нет"
    print("отправлено: ок")

    # человек нажал кнопку
    await db.delivery_opened(111)
    rec = await db.get_delivery("dl-1")
    assert rec["opened_at"], "нажатие кнопки не отметилось"
    assert delivery.stage(rec)[1] == "видел сообщение, файл не брал"
    print("нажал кнопку: ок")

    first_open = rec["opened_at"]
    await db.delivery_opened(111)
    assert (await db.get_delivery("dl-1"))["opened_at"] == first_open, \
        "повторное нажатие не должно переписывать отметку"
    print("повторное нажатие не переписывает время: ок")

    # скачал и подключился
    await db.delivery_downloaded("dl-1")
    assert delivery.stage(await db.get_delivery("dl-1"))[1] == "скачал, но не подключился"
    await db.delivery_connected("dl-1")
    rec = await db.get_delivery("dl-1")
    assert delivery.stage(rec)[1] == "подключился"
    print("скачал и подключился: ок")
    print("  ---\n  " + delivery.describe(rec).replace("\n", "\n  "))

    # скачивание отмечает и «видел», даже если кнопку раньше не ловили
    await db.delivery_sent("dl-4", 444)
    await db.delivery_downloaded("dl-4")
    rec = await db.get_delivery("dl-4")
    assert rec["opened_at"], "скачивание подразумевает, что сообщение видели"
    print("скачивание подразумевает просмотр: ок")

    # не дошло
    await db.delivery_blocked("dl-3", 333, Exception("Forbidden: bot was blocked by the user"))
    rec = await db.get_delivery("dl-3")
    assert rec["blocked_at"] and "blocked" in rec["last_error"]
    assert delivery.stage(rec)[0] == "🚫"
    print("не дошло, причина сохранена: ок")

    # застрявшие: молчун дольше суток и заблокировавший
    await db.delivery_sent("dl-2", 222)
    await db.execute("UPDATE key_delivery SET sent_at = NOW() - INTERVAL '30 hours' "
                     "WHERE user_uuid='dl-2'")
    stuck = {s["user_uuid"] for s in await db.get_stuck_deliveries(24)}
    assert stuck == {"dl-2", "dl-3"}, stuck
    print("в застрявших только те, кто не подключился: ок")
    print("  свежая отправка (dl-4) и дошедший (dl-1) в список не попали")

    # перевыпуск: стадии обнуляются, старые отметки к новому конфигу не относятся
    await db.delivery_sent("dl-1", 111)
    rec = await db.get_delivery("dl-1")
    assert not rec["connected_at"] and not rec["downloaded_at"] and not rec["opened_at"], rec
    print("повторная отправка обнуляет стадии: ок")

    # удаление ключа уносит запись
    await db.execute("DELETE FROM users WHERE uuid='dl-3'")
    assert await db.fetch_val(
        "SELECT COUNT(*) FROM key_delivery WHERE user_uuid='dl-3'") == 0
    print("каскадная чистка: ок")

    # обёртка track_send: успех и неудача
    async def good():
        return True

    async def bad():
        raise Exception("Forbidden: bot was blocked by the user")

    ok, err = await delivery.track_send("dl-2", 222, good)
    assert ok and err is None and (await db.get_delivery("dl-2"))["sent_at"]
    ok, err = await delivery.track_send("dl-2", 222, bad)
    assert not ok and err is not None
    rec = await db.get_delivery("dl-2")
    assert rec["blocked_at"], "неудача должна записываться как состояние доставки"
    print("обёртка отправки пишет оба исхода: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'dl-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
