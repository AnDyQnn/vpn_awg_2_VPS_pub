# -*- coding: utf-8 -*-
"""Мягкий контроль в боте: настройка, отправка узлу, сводка, разделение.

Наблюдение не должно попадать в ленту инцидентов и не должно слаться как
тревога: инцидент — это сработавший запрет, а мягкий режим ничего не режет.
"""
import asyncio
from datetime import datetime, timedelta

from database import db
import filters


SENT = []


class Resp:
    def __init__(self, payload):
        self._p, self.status = payload, 200

    async def json(self):
        return self._p

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class Session:
    def post(self, url, json=None, **kw):
        SENT.append(json)
        return Resp({"status": "ok", "filtered": 0})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM settings WHERE key IN ('filters_watch','filters_common')")
    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'w-%'")

    print("=== настройка хранится ===")
    await db.set_watch_filters(["social", "streaming"])
    assert sorted(await db.get_watch_filters()) == ["social", "streaming"]
    print("ок")

    print("\n=== узлу уходит watch, и без того, что уже режется всем ===")
    await db.set_common_filters(["social"])     # social режем всем
    filters.peer_addr_map = lambda: _amap()
    filters.api_session = lambda: Session()
    SENT.clear()
    ok, msg = await filters.apply_filters("тест")
    assert ok, msg
    payload = SENT[-1]
    assert payload["watch"] == ["streaming"], payload["watch"]
    print("  ушло:", payload["watch"], "— social убран, он и так в общем запрете: ок")

    print("\n=== наблюдение не идёт в ленту инцидентов ===")
    now = datetime.utcnow()
    await db.add_filter_hit(now, "w-uid", "Вова", "10.13.13.9", None,
                            "w-porn.example", "adult", "AAAA-1", watch=True)
    await db.add_filter_hit(now - timedelta(seconds=1), "w-uid", "Вова",
                            "10.13.13.9", None, "w-casino.example", "gambling",
                            "BBBB-2", watch=False)
    incidents = await db.list_filter_hits(limit=50, watch=False)
    obs = await db.list_filter_hits(limit=50, watch=True)
    assert any(h["domain"] == "w-casino.example" for h in incidents)
    assert not any(h["domain"] == "w-porn.example" for h in incidents), \
        "наблюдение просочилось в инциденты"
    assert any(h["domain"] == "w-porn.example" for h in obs)
    print("  инциденты и наблюдение разведены: ок")

    print("\n=== наблюдение не будит сводку инцидентов ===")
    since = await db.hits_since(0)
    assert not any(h["domain"] == "w-porn.example" for h in since), \
        "наблюдение попало в источник тревог"
    print("  hits_since отдаёт только запреты: ок")

    print("\n=== сводка мягкого режима ===")
    summ = await db.watch_summary(168)
    row = [r for r in summ if r["who"] == "Вова" and r["category"] == "adult"]
    assert row and row[0]["hits"] == 1 and row[0]["key"] == "w-uid", summ
    assert await db.watch_total(168) >= 1
    print("  сводка собирается: ок")

    print("\n=== сайты человека ===")
    await db.add_filter_hit(now - timedelta(minutes=5), "w-uid", "Вова", "10.13.13.9",
                            None, "w-video.example", "streaming", "CCCC-3", watch=True)
    sites = await db.watch_person("w-uid", 168)
    doms = [s["domain"] for s in sites]
    assert doms[0] == "w-porn.example" and "w-video.example" in doms, doms
    assert "w-casino.example" not in doms, "запрет в сайты наблюдения не попадает"
    print("  ", doms, "— свежие сверху, только наблюдение: ок")

    print("\n=== свой срок у наблюдения, инциденты по своему ===")
    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'w-%'")
    old = now - timedelta(days=20)
    await db.add_filter_hit(old, "w-uid", "Вова", "10.13.13.9", None,
                            "w-old-watch.example", "social", "D-1", watch=True)
    await db.add_filter_hit(old, "w-uid", "Вова", "10.13.13.9", None,
                            "w-old-incident.example", "gambling", "D-2", watch=False)
    await db.add_filter_hit(now, "w-uid", "Вова", "10.13.13.9", None,
                            "w-new-watch.example", "social", "D-3", watch=True)
    assert await db.watch_keep_days() == 14, "по умолчанию — две недели"
    await db.cleanup_filter_hits()
    doms = {r["domain"] for r in await db.fetch_all(
        "SELECT domain FROM filter_hits WHERE domain LIKE 'w-%'")}
    assert "w-old-watch.example" not in doms, "наблюдение старше 14 дней должно уйти"
    assert "w-old-incident.example" in doms, "инцидент 20 дней — ещё в пределах своих 30"
    assert "w-new-watch.example" in doms
    print("  наблюдение 20 дн. убрано, инцидент 20 дн. оставлен, свежее цело: ок")

    await db.set_watch_keep_days(30)
    assert await db.watch_keep_days() == 30
    print("  срок меняется: ок")

    print("\n=== ручная очистка — только наблюдение ===")
    n = await db.clear_watch_hits()
    doms = {r["domain"] for r in await db.fetch_all(
        "SELECT domain FROM filter_hits WHERE domain LIKE 'w-%'")}
    assert n >= 1 and "w-new-watch.example" not in doms
    assert "w-old-incident.example" in doms, "ручная очистка не трогает инциденты"
    print("  удалено наблюдений: %d, инцидент на месте: ок" % n)

    await db.execute("DELETE FROM filter_hits WHERE domain LIKE 'w-%'")
    await db.execute("DELETE FROM settings WHERE key IN "
                     "('filters_watch','filters_common','watch_keep_days')")
    print("\nВСЁ ПРОШЛО")


async def _amap():
    return {"w-uid": ["10.13.13.9"]}


asyncio.run(main())
