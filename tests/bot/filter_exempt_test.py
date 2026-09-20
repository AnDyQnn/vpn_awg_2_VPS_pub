# -*- coding: utf-8 -*-
"""Личное исключение из общей категории.

До этого общая категория не снималась ни для кого: узел складывал общий список
с личным. Обходом оставалось перечислять домены поштучно в разрешениях — для
категории вроде «для взрослых» это не работает и работать не может.
"""
import asyncio
import json

from database import db
import filters


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def text(self):
        return json.dumps(self._p)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    last = None

    def post(self, url, json=None, timeout=None):
        FakeSession.last = json
        return FakeResp({"status": "ok", "filtered": 1})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'fx-%'")
    for uid, name in (("fx-1", "Владелец"), ("fx-2", "Ребёнок")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
            name, uid)

    filters.api_session = lambda: FakeSession()

    async def addrs():
        return {"fx-1": ["10.13.13.2"], "fx-2": ["10.13.13.3"]}
    filters.peer_addr_map = addrs

    await db.set_common_filters(["adult", "gambling"])

    print("=== пока исключений нет, общее едет всем ===")
    ok, msg = await filters.apply_filters("тест")
    assert ok, msg
    sent = FakeSession.last
    print("  общие:", sent["common"])
    print("  снято лично:", sent.get("except_clients"))
    assert sorted(sent["common"]) == ["adult", "gambling"]
    assert sent.get("except_clients") == {}, sent.get("except_clients")
    print("никто не выведен: ок")

    print("\n=== владелец открывает себе одну категорию ===")
    await db.set_user_exempt("fx-1", "adult", True)
    assert await db.get_user_exempt("fx-1") == ["adult"]
    assert await db.get_user_exempt("fx-2") == [], "чужого это трогать не должно"

    ok, msg = await filters.apply_filters("исключение")
    assert ok, msg
    sent = FakeSession.last
    print("  снято лично:", sent["except_clients"])
    # На узел едут адреса, а не ключи: про людей он не знает.
    assert sent["except_clients"] == {"10.13.13.2": ["adult"]}, sent["except_clients"]
    assert sorted(sent["common"]) == ["adult", "gambling"], "общее не должно меняться"
    print("уехало адресом, общее осталось общим: ок")

    print("\n=== узел считает категории с учётом снятого ===")
    # Повторяем ровно ту арифметику, что делает резолвер, — на той же раскладке,
    # которую мы только что отправили. Иначе проверялся бы код, а не стык.
    common = list(sent["common"])
    for ip, expect in (("10.13.13.2", ["gambling"]),
                       ("10.13.13.3", ["adult", "gambling"])):
        skip = set(sent["except_clients"].get(ip) or ())
        cats = [c for c in common if c not in skip]
        cats += list((sent["clients"].get(ip) or []))
        print("  %s → %s" % (ip, sorted(set(cats))))
        assert sorted(set(cats)) == expect, (ip, cats)
    print("у владельца открыто, у ребёнка закрыто: ок")

    print("\n=== личный запрет сильнее личного исключения ===")
    # Если владелец сам закрыл категорию человеку, исключение из ОБЩЕГО её не
    # открывает: это разные намерения, и путать их нельзя.
    await db.set_user_filter("fx-1", "adult", True)
    ok, msg = await filters.apply_filters("личный запрет поверх")
    sent = FakeSession.last
    skip = set(sent["except_clients"].get("10.13.13.2") or ())
    cats = [c for c in sent["common"] if c not in skip]
    cats += list(sent["clients"].get("10.13.13.2") or [])
    print("  у владельца теперь:", sorted(set(cats)))
    assert "adult" in cats, "личный запрет обязан пережить исключение"
    await db.set_user_filter("fx-1", "adult", False)
    print("личный запрет не снимается исключением из общего: ок")

    print("\n=== возврат под общее правило ===")
    await db.set_user_exempt("fx-1", "adult", False)
    ok, msg = await filters.apply_filters("возврат")
    sent = FakeSession.last
    assert sent["except_clients"] == {}, sent["except_clients"]
    print("исключение снимается так же просто: ок")

    print("\n=== удаление человека уносит его исключения ===")
    await db.set_user_exempt("fx-2", "gambling", True)
    await db.execute("DELETE FROM users WHERE uuid='fx-2'")
    left = await db.get_all_exempt()
    assert "fx-2" not in left, left
    print("хвостов не остаётся: ок")

    await db.set_common_filters([])
    await db.execute("DELETE FROM users WHERE uuid LIKE 'fx-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
