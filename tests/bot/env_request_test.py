# -*- coding: utf-8 -*-
"""Просьбы записать переменную не затирают друг друга.

Бот сам выдаёт токен панелей при первом запуске, владелец в те же минуты задаёт
пароль архива. Обе просьбы ложились в один файл, и не дописыванием, а
перезаписью: кто попал вторым, тот стёр первого. Снаружи это выглядело как
«токен не выдался» или «пароль не применился» — без единого следа.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from utils import FLAGS_DIR, request_env_change, env_change_applied  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-50s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


async def main():
    for old in FLAGS_DIR.glob("set_env*"):
        old.unlink()

    print("=== две просьбы подряд ===")
    a = request_env_change("API_TOKEN", "токен-1")
    b = request_env_change("BACKUP_PASSWORD", "пароль-1")
    check("у каждой свой файл", a != b, "%s / %s" % (a.name, b.name))
    check("обе на месте", a.exists() and b.exists(),
          "раньше вторая стирала первую")

    bodies = sorted(p.read_text(encoding="utf-8").strip() for p in (a, b))
    check("значения не перепутались",
          bodies == sorted(["API_TOKEN=токен-1", "BACKUP_PASSWORD=пароль-1"]),
          " | ".join(bodies))

    print()
    print("=== бот ждёт именно свою ===")
    a.unlink()                       # демон забрал первую
    check("чужая просьба не считается ответом",
          not await env_change_applied(b, timeout=2),
          "иначе бот отчитается об успехе за чужой счёт")
    b.unlink()
    check("своя забрана — применено", await env_change_applied(b, timeout=2))
    check("без файла ответ отрицательный",
          not await env_change_applied(None, timeout=1),
          "молчание не значит успех")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
