# -*- coding: utf-8 -*-
"""Проверка срока и спячки ключа: вопросы, политика, тексты. В прод не уезжает."""
import asyncio
from datetime import datetime, timedelta

from database import db


async def main():
    await db.connect()
    print("подключение и миграции: ок")

    for table in ("pending_decisions", "key_policy"):
        exists = await db.fetch_val(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1", table)
        print(f"  таблица {table}: {'есть' if exists else 'НЕТ'}")
        assert exists

    await db.execute("DELETE FROM users WHERE uuid LIKE 'kl-%'")
    old = datetime.utcnow() - timedelta(days=40)
    await db.execute(
        "INSERT INTO users (name, uuid, created_at, last_active_at, expires_at) "
        "VALUES ('Просроченный','kl-1',$1,$1,$2)", old,
        datetime.utcnow() - timedelta(days=2))
    await db.execute(
        "INSERT INTO users (name, uuid, created_at, last_active_at) "
        "VALUES ('Спящий','kl-2',$1,$1)", old)

    await db.add_pending_decision("kl-1", "expired", old,
                                  datetime.utcnow() - timedelta(days=2))
    await db.add_pending_decision("kl-2", "dormant", old)
    items = await db.get_pending_decisions()
    assert len(items) == 2, items
    print("вопросы заведены: ок")

    # повторный проход цикла не должен задать вопрос второй раз
    await db.add_pending_decision("kl-1", "expired", old)
    assert len(await db.get_pending_decisions()) == 2, "вопрос задвоился"
    print("повторный проход не плодит вопросы: ок")

    # политика по умолчанию — спрашивать
    pol = await db.get_key_policy("kl-1")
    assert pol["mode"] == "ask" and pol["extend_days"] is None, pol
    print("умолчание политики — спрашивать: ок")

    # тексты вопроса собираются и различаются по причине
    import handlers_keylife as kl
    t1 = await kl.decision_text("kl-1")
    t2 = await kl.decision_text("kl-2")
    assert "Истёк срок" in t1 and "Срок был до" in t1, t1
    assert "Ключ уснул" in t2 and "Не подключался" in t2, t2
    assert "на паузе" in t1
    print("тексты вопросов: ок")
    print("  ---\n  " + t1.replace("\n", "\n  "))

    # клавиатура ведёт на решение именно по этому ключу
    kb = kl.decision_keyboard("kl-1").inline_keyboard
    datas = [b.callback_data for row in kb for b in row]
    assert "kd_ext_kl-1" in datas and "kd_del_kl-1" in datas, datas
    assert all(len(d.encode()) <= 64 for d in datas), "callback_data длиннее 64 байт"
    print("кнопки вопроса: ок")

    # длина callback_data на реальном uuid: 36 символов
    real = "kd_set_90_" + "8f14e45f-ceea-467a-9f43-1b2c3d4e5f60"
    assert len(real.encode()) <= 64, len(real)
    print(f"  самая длинная callback_data: {len(real)} байт из 64")

    # решение закрывает вопрос и не мешает задать новый потом
    await db.resolve_decision("kl-1", "extended:30")
    assert len(await db.get_pending_decisions()) == 1
    assert await db.get_pending_decision("kl-1") is None
    print("решение закрывает вопрос: ок")

    await db.add_pending_decision("kl-1", "expired", old)
    assert await db.get_pending_decision("kl-1"), "новый вопрос должен заводиться"
    hist = await db.fetch_val(
        "SELECT COUNT(*) FROM pending_decisions WHERE user_uuid='kl-1'")
    assert hist == 2, f"история решений потерялась: {hist}"
    print("история решений сохраняется, новый вопрос заводится: ок")

    # автопродление
    await db.set_key_policy("kl-1", "auto", 30)
    pol = await db.get_key_policy("kl-1")
    assert pol["mode"] == "auto" and pol["extend_days"] == 30
    await db.set_key_policy("kl-1", "ask", None)
    assert (await db.get_key_policy("kl-1"))["mode"] == "ask"
    print("политика переключается в обе стороны: ок")

    # порог спячки читается из настроек, а не захардкожен
    assert await kl.dormant_days() == 30
    await db.set_setting("dormant_days", "45")
    assert await kl.dormant_days() == 45
    await db.execute("DELETE FROM settings WHERE key='dormant_days'")
    print("порог спячки берётся из настроек: ок")

    # удаление ключа уносит и вопрос, и политику
    await db.set_key_policy("kl-2", "auto", 7)
    await db.execute("DELETE FROM users WHERE uuid='kl-2'")
    left = await db.fetch_val(
        "SELECT COUNT(*) FROM pending_decisions WHERE user_uuid='kl-2'")
    pol_left = await db.fetch_val(
        "SELECT COUNT(*) FROM key_policy WHERE user_uuid='kl-2'")
    assert left == 0 and pol_left == 0, (left, pol_left)
    print("удаление ключа уносит вопрос и политику каскадом: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'kl-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
