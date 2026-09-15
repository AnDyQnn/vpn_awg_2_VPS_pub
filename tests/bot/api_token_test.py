# -*- coding: utf-8 -*-
"""Токен панелей доводится до одинакового состояния сам.

Выдача была разовым действием: сгенерировать, разослать, записать отметку
«выдан». Результат не проверялся, поэтому потеря по дороге — а терялась она
тихо — делала отметку ложью. Бот считал дело сделанным, панели оставались
открытыми, и заметить это было нечем.

Проверяется то, ради чего переписано:
  • токена нет — выдаём и дожидаемся, что запись ПРИМЕНИЛАСЬ;
  • не применилась — отметку не ставим и говорим владельцу;
  • токен есть, у Германии нет — досылаем;
  • Германия молчит — ничего не трогаем: она принимает мастера и без токена.
"""
import asyncio
import sys

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
    await db.execute("DELETE FROM settings WHERE key='api_token_issued_at'")

    pushed = []
    status = {"value": None}

    async def fake_status():
        return status["value"]

    async def fake_push(token):
        pushed.append(token)
        return True

    hs._de_env_status = fake_status
    hs._push_token_to_de = fake_push

    print("=== токена нет, а служба обновлений молчит ===")
    utils.API_TOKEN = ""
    told.clear()
    await hs.ensure_api_token(App())
    left = list(utils.FLAGS_DIR.glob("set_env*"))
    check("просьба записана", len(left) == 1, "файлов: %d" % len(left))
    check("в ней токен панелей",
          left and left[0].read_text(encoding="utf-8").startswith("API_TOKEN="))
    check("отметку «выдан» НЕ поставили",
          not await db.get_setting("api_token_issued_at"),
          "иначе бот запомнит несделанное как сделанное")
    check("владельцу сказали", any("vpn-updater" in t for t in told),
          "молчание выглядит как успех")
    check("на Германию ничего не слали", not pushed,
          "нельзя раздавать токен, которого у мастера нет")

    print()
    print("=== служба забрала просьбу ===")
    for f in left:
        f.unlink()
    told.clear()

    async def fake_daemon():
        """Демон на хосте забирает файл, когда применил. Изображаем его именно
        во время ожидания: удалить файл заранее нельзя — бот кладёт новый."""
        for _ in range(50):
            files = list(utils.FLAGS_DIR.glob("set_env*"))
            if files:
                for f in files:
                    f.unlink()
                return
            await asyncio.sleep(0.1)

    await asyncio.gather(hs.ensure_api_token(App()), fake_daemon())
    check("теперь отметка стоит",
          bool(await db.get_setting("api_token_issued_at")))
    check("владельцу сказали, что выдан",
          any("выдан" in t for t in told), "; ".join(told)[:60])

    print()
    print("=== токен есть, у Германии нет ===")
    utils.API_TOKEN = "живой-токен"
    status["value"] = {"API_TOKEN": False}
    pushed.clear()
    told.clear()
    await hs.ensure_api_token(App())
    check("досылаем именно его", pushed == ["живой-токен"], str(pushed))

    print()
    print("=== у Германии он уже есть ===")
    status["value"] = {"API_TOKEN": True}
    pushed.clear()
    await hs.ensure_api_token(App())
    check("второй раз не шлём", not pushed, "лишняя запись — лишний перезапуск")

    print()
    print("=== Германия молчит ===")
    status["value"] = None
    pushed.clear()
    await hs.ensure_api_token(App())
    check("ничего не трогаем", not pushed,
          "она принимает мастера и без токена — ломать нечего")

    utils.API_TOKEN = ""
    for f in utils.FLAGS_DIR.glob("set_env*"):
        f.unlink()
    await db.execute("DELETE FROM settings WHERE key='api_token_issued_at'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
