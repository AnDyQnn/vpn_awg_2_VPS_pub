# -*- coding: utf-8 -*-
"""Бот дожидается узла, а не сдаётся на первой секунде.

Найдено на бою сразу после обновления. Бот стартует через секунду после
контейнера узла и тут же идёт к его панели — а та ещё поднимается. Первый
запрос падает, и вместе с ним падает всё восстановление состояния: роли,
фильтры, имена, конфиг Xray. Повторять бот не пробовал.

Последствия были видны: на узле оказался один вход Xray вместо трёх, хотя бот
знал про три, и раскладка ролей стояла устаревшая, пока владелец не нажал
«Применить» руками.

Проверяется:
  • узел отвечает сразу — ждём один раз и идём дальше;
  • узел поднимается не сразу — дожидаемся, а не сдаёмся;
  • узел не отвечает вовсе — сдаёмся по сроку и не виснем навсегда;
  • ожидание не длиннее заданного срока.
"""
import asyncio
import sys
import time

sys.path.insert(0, "/app")

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeResp:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """Отвечает отказом первые `fail` раз, потом успехом."""
    fail = 0
    tries = 0

    def get(self, url, **kw):
        FakeSession.tries += 1
        if FakeSession.tries <= FakeSession.fail:
            raise OSError("узел ещё поднимается")
        return FakeResp(200)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    import bot as b
    import utils

    utils.api_session = lambda: FakeSession()
    # Внутри функции сессия берётся из utils по месту вызова — подменяем там же.
    sys.modules["utils"].api_session = lambda: FakeSession()

    print("=== узел отвечает сразу ===")
    FakeSession.fail, FakeSession.tries = 0, 0
    started = time.monotonic()
    got = await b.wait_for_node(timeout=10)
    check("дождались", got is True)
    check("попытка одна", FakeSession.tries == 1, "%d" % FakeSession.tries)
    check("не тянули время", time.monotonic() - started < 1,
          "%.1f с" % (time.monotonic() - started))

    print()
    print("=== узел поднимается не сразу ===")
    FakeSession.fail, FakeSession.tries = 2, 0
    started = time.monotonic()
    got = await b.wait_for_node(timeout=20)
    check("всё равно дождались", got is True,
          "раньше здесь бот сдавался и оставлял узел без ролей")
    check("попыток было больше одной", FakeSession.tries > 1,
          "%d" % FakeSession.tries)

    print()
    print("=== узел не отвечает вовсе ===")
    FakeSession.fail, FakeSession.tries = 10 ** 6, 0
    started = time.monotonic()
    got = await b.wait_for_node(timeout=5)
    spent = time.monotonic() - started
    check("сдались, а не зависли", got is False)
    check("уложились в срок", spent < 9, "%.1f с при сроке 5" % spent)
    check("пытались несколько раз", FakeSession.tries >= 2,
          "%d" % FakeSession.tries)


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
