# -*- coding: utf-8 -*-
"""Недельный отчёт об обслуживании: что в нём и когда он приходит.

Проверяется не «функция не падает», а то, ради чего она написана:

  • одна цифра ни о чём не говорит — рядом обязана быть прошлая неделя;
  • расхождения базы с узлом должны быть видны списком, а не числом;
  • Германия попадает в отчёт, хотя своего бота у неё нет;
  • отчёт приходит раз в неделю, а не каждый час воскресенья;
  • Германия молчит — отчёт всё равно должен прийти, хотя бы про мастер.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, "/app")

import monitor                                   # noqa: E402
from database import db                          # noqa: E402

FLAGS = "/volumes/flags"
os.makedirs(FLAGS, exist_ok=True)

ok = True
SENT = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def fake_notify(app, text, **kw):
    SENT.append(text)
    return None


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    payload = None

    def get(self, url, **kw):
        if FakeSession.payload is None:
            raise RuntimeError("Германия недоступна")
        return FakeResp(FakeSession.payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def put(name, data):
    with open(os.path.join(FLAGS, name), "w") as f:
        json.dump(data, f)


def drop(name):
    try:
        os.remove(os.path.join(FLAGS, name))
    except OSError:
        pass


async def fire(when):
    """Один заход цикла в заданный момент времени."""
    SENT.clear()
    monitor.get_moscow_now = lambda: when
    task = asyncio.ensure_future(monitor.weekly_health_loop(None))
    await asyncio.sleep(0.5)
    task.cancel()
    return SENT[0] if SENT else None


async def run():
    await db.connect()
    monitor.notify_admin = fake_notify
    monitor.api_session = lambda: FakeSession()

    SUNDAY = datetime(2026, 9, 20, 7, 5)

    put("host_health.json", {"ts": 1, "disk_used_pct": 52, "var_log_mb": 210,
                             "reboot_required": False, "packages_upgradable": 3})
    put("gc.json", {"ts": 1, "freed_mb": 880})
    put("contract.json", {"ts": 1, "ok": 7, "warning": 0, "error": 0,
                          "answered": True, "lines": []})
    FakeSession.payload = {
        "health": {"disk_used_pct": 41, "reboot_required": False,
                   "packages_upgradable": 0},
        "gc": {"freed_mb": 1204}}

    await db.set_setting("last_weekly_health", "")
    await db.set_setting("weekly_health_prev", "")

    print("=== первый отчёт: прошлой недели ещё нет ===")
    msg = await fire(SUNDAY)
    check("отчёт пришёл", msg is not None)
    check("мастер в отчёте", msg and "Мастер" in msg)
    check("Германия в отчёте", msg and "Германия" in msg)
    check("уборка мастера", msg and "880 МБ" in msg)
    check("уборка Германии", msg and "1204 МБ" in msg)
    check("сверка сошлась", msg and "всё сошлось" in msg)
    check("без выдуманного «было»", msg and "было" not in msg)

    print()
    print("=== в тот же день второй раз не приходит ===")
    msg2 = await fire(datetime(2026, 9, 20, 7, 40))
    check("повтора нет", msg2 is None)

    print()
    print("=== неделю спустя: цифры рядом с прошлыми ===")
    await db.set_setting("last_weekly_health", "")
    put("host_health.json", {"ts": 2, "disk_used_pct": 61, "reboot_required": True,
                             "packages_upgradable": 42})
    put("gc.json", {"ts": 2, "freed_mb": 0})
    put("contract.json", {"ts": 2, "ok": 5, "warning": 1, "error": 2,
                          "answered": True, "lines": [
                              {"status": "error", "name": "Имена внутри туннеля",
                               "msg": "1 из базы не разложены (дом)"},
                              {"status": "error", "name": "Туннель до Германии",
                               "msg": "молчит 42 мин"},
                              {"status": "ok", "name": "Пиры", "msg": "31"}]})
    msg = await fire(datetime(2026, 9, 27, 7, 5))
    check("диск против прошлой недели", msg and "было 52" in msg, "61% (было 52%)")
    check("рост показан знаком", msg and "+9" in msg)
    check("расхождения числом", msg and "Расхождений базы и узла: 2" in msg)
    check("и списком тоже", msg and "молчит 42 мин" in msg)
    check("вторая строка списка", msg and "не разложены (дом)" in msg)
    check("нужна перезагрузка", msg and "Нужна перезагрузка" in msg)
    check("очередь пакетов", msg and "42" in msg)
    check("уборка без находок", msg and "заметного мусора не было" in msg)

    print()
    print("=== расхождения ушли — об этом сказано отдельно ===")
    await db.set_setting("last_weekly_health", "")
    put("contract.json", {"ts": 3, "ok": 7, "warning": 0, "error": 0,
                          "answered": True, "lines": []})
    msg = await fire(datetime(2026, 10, 4, 7, 5))
    check("упомянута прошлая неделя", msg and "было расхождений: 2" in msg)

    print()
    print("=== Германия молчит: отчёт всё равно приходит ===")
    await db.set_setting("last_weekly_health", "")
    FakeSession.payload = None
    msg = await fire(datetime(2026, 10, 11, 7, 5))
    check("отчёт пришёл", msg is not None)
    check("мастер на месте", msg and "Мастер" in msg)
    check("про Германию сказано честно",
          msg and "обслуживание ещё не отрабатывало" in msg)

    print()
    print("=== будни и другое время: молчит ===")
    await db.set_setting("last_weekly_health", "")
    check("среда", await fire(datetime(2026, 10, 7, 7, 5)) is None)
    check("воскресенье, но полдень",
          await fire(datetime(2026, 10, 11, 12, 0)) is None)

    for n in ("host_health.json", "gc.json", "contract.json"):
        drop(n)


asyncio.get_event_loop().run_until_complete(run())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
