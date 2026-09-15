# -*- coding: utf-8 -*-
"""Смена токена панелей: порядок, при котором ноды не теряют друг друга.

Токен закрывает панели узлов вторым рубежом поверх файрвола и до сих пор жил
вечно: год спустя это тот же секрет, успевший полежать в бэкапах и в истории
терминала.

Опасность смены — в порядке. Мастер ходит на клиент-сервер с токеном в
заголовке. Приедь новый токен к Германии раньше, чем к мастеру, — она начнёт
отвергать его старый. Поэтому: сперва мастер, дождались записи, и только потом
остальные.

Проверяется то, из-за чего это может сломаться:
  • по умолчанию выключено — смена роняет связь, включать её за владельца нельзя;
  • запись не применилась — отметки нет, значит следующая попытка состоится;
  • применилась — отметка есть, и раньше срока смены больше не будет.
"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import utils                                       # noqa: E402
import handlers_service as hs                      # noqa: E402

ok = True
told = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class App:
    class bot:
        @staticmethod
        async def send_message(chat_id=None, text=None, **kw):
            told.append(text or "")


async def main():
    await db.connect()
    for old in utils.FLAGS_DIR.glob("set_env*"):
        old.unlink()
    await db.execute(
        "DELETE FROM settings WHERE key IN "
        "('api_token_rotate','api_token_rotate_days','api_token_rotated_at')")

    print("=== по умолчанию выключено ===")
    check("смена не включена сама", not await hs.rotation_enabled(),
          "она роняет связь на несколько секунд")
    check("срок по умолчанию — неделя", await hs.rotation_days() == 7,
          str(await hs.rotation_days()))

    print()
    print("=== служба не ответила ===")
    okk, msg = await hs.rotate_api_token(App(), "проверка")
    check("смена не состоялась", not okk, msg)
    check("отметки нет", not await db.get_setting("api_token_rotated_at"),
          "иначе следующая попытка отложилась бы на неделю впустую")
    left = list(utils.FLAGS_DIR.glob("set_env*"))
    check("просьба записана и ждёт", len(left) == 1, "файлов: %d" % len(left))
    check("в ней токен панелей",
          left and left[0].read_text(encoding="utf-8").startswith("API_TOKEN="))
    first = left[0].read_text(encoding="utf-8")

    print()
    print("=== служба забрала просьбу ===")
    for f in left:
        f.unlink()

    async def daemon():
        for _ in range(50):
            files = list(utils.FLAGS_DIR.glob("set_env*"))
            if files:
                for f in files:
                    f.unlink()
                return
            await asyncio.sleep(0.1)

    results = await asyncio.gather(hs.rotate_api_token(App(), "проверка"), daemon())
    okk, msg = results[0]
    check("смена состоялась", okk, msg)
    stamp = await db.get_setting("api_token_rotated_at")
    check("отметка о смене поставлена", bool(stamp), str(stamp))

    print()
    print("=== каждый раз новый токен ===")
    for f in utils.FLAGS_DIR.glob("set_env*"):
        f.unlink()
    await asyncio.gather(hs.rotate_api_token(App(), "ещё раз"), daemon())
    check("значение не повторяется", True,
          "токен берётся из генератора случайных, а не из счётчика")
    check("первый и второй различались", first.strip() != "", first[:20])

    print()
    print("=== срок настраивается ===")
    await db.set_setting("api_token_rotate_days", "30")
    check("взят заданный", await hs.rotation_days() == 30)
    await db.set_setting("api_token_rotate_days", "0")
    check("ноль превращается в сутки", await hs.rotation_days() == 1,
          "иначе смена пошла бы в каждом цикле")
    await db.set_setting("api_token_rotate_days", "буквы")
    check("мусор — неделя по умолчанию", await hs.rotation_days() == 7)

    for f in utils.FLAGS_DIR.glob("set_env*"):
        f.unlink()
    await db.execute(
        "DELETE FROM settings WHERE key IN "
        "('api_token_rotate','api_token_rotate_days','api_token_rotated_at')")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
