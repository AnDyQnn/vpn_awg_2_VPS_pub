# -*- coding: utf-8 -*-
"""Сторона бота: хранение фильтров и сборка раскладки для узла."""
import asyncio

from database import db
import filters as F


async def main():
    await db.connect()
    exists = await db.fetch_val(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='user_filters'")
    assert exists
    print("таблица user_filters: есть")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ft-%'")
    for uid, name in (("ft-1", "Младший"), ("ft-2", "Кент")):
        await db.execute("INSERT INTO users (name, uuid) VALUES ($1,$2)", name, uid)

    assert await db.get_user_filters("ft-1") == []
    assert await db.count_filtered_users() == 0
    print("по умолчанию фильтров нет: ок")

    await db.set_user_filter("ft-1", "adult", True)
    await db.set_user_filter("ft-1", "gambling", True)
    await db.set_user_filter("ft-2", "ads", True)
    assert await db.get_user_filters("ft-1") == ["adult", "gambling"]
    assert await db.count_filtered_users() == 2
    print("включение категорий: ок")

    await db.set_user_filter("ft-1", "adult", True)
    assert await db.get_user_filters("ft-1") == ["adult", "gambling"], "дубликат категории"
    print("повторное включение не дублируется: ок")

    await db.set_user_filter("ft-1", "gambling", False)
    assert await db.get_user_filters("ft-1") == ["adult"]
    print("снятие категории: ок")

    all_f = await db.get_all_filters()
    assert all_f == {"ft-1": ["adult"], "ft-2": ["ads"]}, all_f
    print("раскладка по людям: ок")

    # Сборка для узла: только те, у кого есть адрес и категории.
    # У человека может быть два адреса сразу — пир и двойник Xray; фильтр
    # должен лечь на оба, иначе он перестанет работать при смене протокола.
    async def fake_ips():
        return {"ft-1": ["10.13.13.5", "10.13.13.133"]}   # у второго адреса ещё нет

    F.peer_addr_map = fake_ips
    sent = {}

    class Resp:
        status = 200

        async def json(self):
            return {"filtered": len(sent.get("clients", {}))}

        async def text(self):
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class Session:
        def post(self, url, json=None, timeout=None):
            sent.update(json)
            return Resp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    F.api_session = lambda: Session()
    ok, msg = await F.apply_filters("тест")
    assert ok, msg
    assert sent["clients"] == {"10.13.13.5": ["adult"],
                               "10.13.13.133": ["adult"]}, sent
    print("на узел уходят оба адреса человека, и только с категориями: ок")
    print(" ", msg)

    # категории, которые показывает бот, совпадают с теми, что знает узел
    import io, ast
    node = io.open("/app/api_categories.txt", encoding="utf-8").read().split()
    bot_cats = [c for c, _ in F.CATEGORIES]
    assert sorted(bot_cats) == sorted(node), (bot_cats, node)
    print("список категорий в боте и на узле совпадает: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ft-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
