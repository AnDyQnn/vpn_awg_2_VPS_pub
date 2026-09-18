# -*- coding: utf-8 -*-
"""Выдача ключа себе не приходит дважды.

Владелец: «я когда выпускаю или перевыпускаю конфиги, они мне по два раза
приходят».

Так и было устроено. Выдача шлёт две порции: копию владельцу — всегда, потому
что без привязанного Telegram ссылку надо передать как-то иначе, — и то же
самое человеку, которому ключ предназначен. Пока это разные люди, всё честно.
Но владелец выдаёт ключи в основном себе, и его Telegram привязан ещё к
полудюжине чужих ключей. Тогда обе порции летят в один чат: два одинаковых QR,
две одинаковые ссылки подряд.

Лишней здесь оказывается именно копия владельцу: человеку уходит более полный
набор — с подсказкой, что ставить и куда вставлять.

Но и молчать нельзя, если человеку не дошло: остаться совсем без ссылки хуже,
чем получить её дважды. Поэтому придержанная копия отдаётся при неудаче.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402
from delivery import to_self                       # noqa: E402

ok = True
ADMIN = 1288136291
OTHER = 5413942695


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Bot:
    """Считает, что и в какой чат ушло."""

    def __init__(self):
        self.sent = []          # (chat_id, вид)

    async def send_message(self, chat_id=None, text="", **k):
        # Ссылка уходит отдельным сообщением: её и считаем доступом.
        kind = "доступ" if "vless://" in str(text) or "https://" in str(text) else "текст"
        self.sent.append((chat_id, kind))

    async def send_photo(self, chat_id=None, **k):
        self.sent.append((chat_id, "QR"))

    async def send_document(self, chat_id=None, **k):
        self.sent.append((chat_id, "файл"))

    def count(self, chat_id, kind):
        return sum(1 for c, k in self.sent if c == chat_id and k == kind)


class Ctx:
    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}


class Upd:
    def __init__(self, chat_id):
        self.effective_chat = type("C", (), {"id": chat_id})()
        self.effective_user = type("U", (), {"id": chat_id})()
        self.callback_query = None


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid='dbl-1'")
    await db.execute("DELETE FROM users WHERE uuid='dbl-1'")
    await db.execute("INSERT INTO users (name, uuid, is_active) "
                     "VALUES ('Свой','dbl-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('dbl-1','x-dbl','tok-dbl-0123456789')")

    print("=== кто получатель ===")
    check("тот же человек", to_self(ADMIN, ADMIN))
    check("число и строка — это один человек", to_self(ADMIN, str(ADMIN)),
          "из базы номер приходит строкой, и == тихо давал «разные»")
    check("другой человек", not to_self(ADMIN, OTHER))
    check("Telegram не привязан", not to_self(ADMIN, None),
          "тогда копия владельцу — единственный способ передать ключ")

    # Узла в тестах нет: подменяем всё, что к нему ходит. Проверяем не выдачу
    # ключа, а то, сколько раз она приходит в чат.
    import restrictions
    import handlers_client
    import handlers_xray as HX

    xray.issue = lambda uuid_val, new_address=False: _ok()
    xray.bundle_text = lambda uuid_val: _text("vless://dbl@1.2.3.4#Свой")
    xray.qr_file = lambda uuid_val: _text("")
    restrictions.reapply = lambda *a, **k: _none()
    HX.instructions = lambda uuid_val: _text("как подключить")

    delivered = {"ok": True}

    async def fake_profile(context, chat_id, uuid_val):
        if not delivered["ok"]:
            return False
        await context.bot.send_photo(chat_id=chat_id)
        await context.bot.send_message(chat_id=chat_id,
                                       text="vless://dbl@1.2.3.4#Свой")
        return True

    handlers_client.send_xray_profile = fake_profile

    print()
    print("=== ключ себе ===")
    bot = Bot()
    await HX.handout(Upd(ADMIN), Ctx(bot), "dbl-1", "Свой", ADMIN)
    check("доступ пришёл один раз", bot.count(ADMIN, "доступ") == 1,
          "пришло %d" % bot.count(ADMIN, "доступ"))
    check("и QR один раз", bot.count(ADMIN, "QR") == 1,
          "пришло %d" % bot.count(ADMIN, "QR"))

    print()
    print("=== ключ другому человеку ===")
    bot = Bot()
    await HX.handout(Upd(ADMIN), Ctx(bot), "dbl-1", "Дима", OTHER)
    check("человек получил доступ", bot.count(OTHER, "доступ") == 1,
          "пришло %d" % bot.count(OTHER, "доступ"))
    check("владелец тоже получил — передать некому иначе",
          bot.count(ADMIN, "доступ") == 1,
          "пришло %d" % bot.count(ADMIN, "доступ"))

    print()
    print("=== себе, но отправка человеку не прошла ===")
    delivered["ok"] = False
    bot = Bot()
    await HX.handout(Upd(ADMIN), Ctx(bot), "dbl-1", "Свой", ADMIN)
    check("доступ всё равно пришёл", bot.count(ADMIN, "доступ") == 1,
          "без ссылки остаться хуже, чем получить её дважды")
    delivered["ok"] = True

    print()
    print("=== то же самое на пути AmneziaWG ===")
    src = open("/app/handlers_users.py", encoding="utf-8").read()
    part = src[src.index("Ключ сгенерирован!"):][:1200]
    check("копия владельцу придержана", "if not mine:" in part,
          "иначе конфиг и QR приходят себе же дважды")
    check("при неудаче отдаётся", "if mine and not ok:" in src)

    await db.execute("DELETE FROM xray_users WHERE user_uuid='dbl-1'")
    await db.execute("DELETE FROM users WHERE uuid='dbl-1'")


async def _ok():
    return True, ""


async def _none():
    return None


async def _text(v):
    return v


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
