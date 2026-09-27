# -*- coding: utf-8 -*-
"""Оповещения о нагрузке: по делу, с причиной, без шума.

Узлы одноядерные. Раньше тревога шла по одному замеру — короткий пик от
выкладки, обновления системы или копии будил владельца «периодически», и из
сообщения нельзя было понять, кто грузит.

Проверяется на настоящем цикле проверки ресурсов:
  • один пик — тишина;
  • перегрузка две проверки подряд — тревога, в ней кто грузит;
  • если грузит плановая работа (сборка при выкладке) — тревоги нет, но
    случай записан в журнал.
"""
import asyncio
import json
import os
import time

import psutil

from database import db
import monitor


class Stop(Exception):
    pass


class Resp:
    status = 200

    async def json(self):
        return {"ram": 10, "disk": 10, "load1": 0.1, "cores": 1}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class Session:
    def get(self, url, **kw):
        return Resp()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


SENT = []


async def fake_notify(app, text, **kw):
    SENT.append(text)


def write_top(comm, cpu):
    os.makedirs("/volumes/flags", exist_ok=True)
    json.dump({"ts": time.time(), "load1": 2.0, "load5": 1.8, "cores": 1,
               "top": [{"comm": comm, "cpu": cpu}, {"comm": "python3", "cpu": 5}]},
              open(monitor.LOAD_TOP_FILE, "w"))


async def run_loop(loads):
    """Прогоняет цикл len(loads) раз с заданной нагрузкой на каждом круге."""
    it = iter(loads)
    state = {"n": 0}

    async def fake_sleep(_):
        state["n"] += 1
        if state["n"] > len(loads):
            raise Stop()
        os.getloadavg = lambda v=next(it): (v, v, v)

    monitor.asyncio.sleep = fake_sleep
    try:
        await monitor.resource_monitor_loop(None)
    except Stop:
        pass


async def main():
    await db.connect()
    monitor.api_session = lambda: Session()
    monitor.notify_admin = fake_notify
    psutil.cpu_count = lambda *a, **k: 1

    print("=== один пик — тишина ===")
    monitor.resource_alert_cache.clear()
    monitor._overload_streak.update(RU=0, DE=0)
    SENT.clear()
    write_top("wireguard-go", 90)
    await run_loop([2.5, 0.3, 2.5])
    assert not SENT, SENT
    print("ок")

    print("\n=== перегрузка держится — тревога с причиной ===")
    monitor.resource_alert_cache.clear()
    monitor._overload_streak.update(RU=0, DE=0)
    SENT.clear()
    write_top("wireguard-go", 90)
    await run_loop([2.5, 2.5])
    assert len(SENT) == 1, SENT
    print("  " + SENT[0].replace("\n", " | ")[:200])
    assert "wireguard-go 90%" in SENT[0] and "шифрование трафика" in SENT[0]
    print("ок")

    print("\n=== грузит плановая работа — тревоги нет, в журнале есть ===")
    monitor.resource_alert_cache.clear()
    monitor._overload_streak.update(RU=0, DE=0)
    SENT.clear()
    await db.execute("DELETE FROM events_log WHERE event_type='Load'")
    write_top("dockerd", 80)
    await run_loop([2.5, 2.5, 2.5])
    assert not SENT, SENT
    n = await db.fetch_val("SELECT COUNT(*) FROM events_log WHERE event_type='Load' "
                           "AND message LIKE '%dockerd%'")
    assert n >= 1, n
    print("  записей в журнале: %d, тревог: 0 — ок" % n)

    await db.execute("DELETE FROM events_log WHERE event_type='Load'")
    os.remove(monitor.LOAD_TOP_FILE)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
