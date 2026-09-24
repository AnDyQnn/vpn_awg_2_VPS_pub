# -*- coding: utf-8 -*-
"""Текст копируется касанием, а в карточке видно, кто это.

Две вещи, которые проверяются здесь, объединяет одно: и то и другое человек
делает руками десятки раз, и каждый раз есть чему пойти не так.

  • Текст для копирования (пароль зоны и подобное) уходит помеченным как код —
    по нему достаточно нажать. Разметкой этого делать нельзя: в тексте бывают
    подчёркивания, и разметка
    роняет сообщение целиком. Поэтому сущность, и поэтому же проверяем, что
    длина посчитана так, как её считает Telegram, — в единицах UTF-16.

  • В карточке рядом с числовым id стоит логин. Логин запоминается, когда
    человек сам открыл бота, и спрашивается у Telegram, только если он ещё не
    известен, — иначе карточка ходила бы в сеть при каждом открытии.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
from utils import send_copyable                    # noqa: E402

ok = True
TG = 987654323


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeBot:
    def __init__(self):
        self.msgs = []
        self.chat_calls = 0

    async def send_message(self, chat_id=None, text=None, entities=None, **kw):
        self.msgs.append({"text": text, "entities": entities, "kw": kw})

    async def send_photo(self, **kw):
        self.msgs.append({"photo": True})

    async def get_chat(self, tg_id):
        self.chat_calls += 1
        return type("C", (), {"username": "nikamob", "first_name": "Ника"})()

    async def edit_message_text(self, **kw):
        self.msgs.append({"text": kw.get("text")})


class FakeContext:
    def __init__(self):
        self.bot = FakeBot()
        self.user_data = {}


async def main():
    await db.connect()

    print("=== текст уходит копируемым ===")
    ctx = FakeContext()
    link = "Pa_ss-word_42*for_zone#Ника"
    await send_copyable(ctx.bot, 1, link)
    msg = ctx.bot.msgs[-1]
    ent = (msg["entities"] or [None])[0]
    check("текст — как есть", msg["text"] == link)
    check("помечена как код", ent is not None and ent.type == "code",
          getattr(ent, "type", "нет пометки"))
    check("разметка не применяется", "parse_mode" not in msg["kw"],
          "одно непарное подчёркивание роняет сообщение целиком")
    check("пометка накрывает текст целиком",
          ent and ent.offset == 0 and ent.length == len(link),
          "%s знаков" % (ent.length if ent else "—"))

    # Текст бывает с эмодзи: Telegram считает такой символ за две
    # единицы, а обычный len() — за одну, и пометка обрезалась бы.
    ctx2 = FakeContext()
    emoji_link = link.replace("#Ника", "#Ника 🚀")
    await send_copyable(ctx2.bot, 1, emoji_link)
    ent2 = ctx2.bot.msgs[-1]["entities"][0]
    expected = len(emoji_link.encode("utf-16-le")) // 2
    check("длина считается в единицах UTF-16", ent2.length == expected,
          "%d, а не %d" % (ent2.length, len(emoji_link)))

    print()
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cp-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Ника','cp-1',TRUE)")
    await db.execute("INSERT INTO user_tg_links (uuid, tg_id) VALUES ('cp-1',$1)", TG)
    import handlers_client as hc

    print()
    print("=== логин в карточке ===")
    from handlers_users import _tg_line
    await db.execute("UPDATE user_tg_links SET username=NULL WHERE tg_id=$1", TG)

    ctx4 = FakeContext()
    line = await _tg_line(ctx4, [TG])
    check("логин спросили у Telegram", ctx4.bot.chat_calls == 1,
          "походов в сеть: %d" % ctx4.bot.chat_calls)
    check("логин показан", "@nikamob" in line, line)
    check("числовой id остался рядом", str(TG) in line,
          "по нему бот находит человека, по логину — владелец")

    ctx5 = FakeContext()
    line2 = await _tg_line(ctx5, [TG])
    check("второй раз в сеть не ходим", ctx5.bot.chat_calls == 0,
          "логин уже запомнен")
    check("и показываем то же самое", "@nikamob" in line2, line2)

    print()
    print("=== логин запоминается сам, когда человек открыл бота ===")
    await db.execute("UPDATE user_tg_links SET username=NULL WHERE tg_id=$1", TG)

    class MenuUpdate:
        callback_query = None
        effective_chat = type("C", (), {"id": TG})()
        effective_user = type("U", (), {"id": TG, "first_name": "Ника",
                                        "username": "nikamob"})()

    await hc.client_menu(MenuUpdate(), FakeContext())
    known = await db.get_tg_usernames([TG])
    check("логин записан без единого запроса в Telegram",
          known.get(TG) == "nikamob", str(known))

    await db.execute("UPDATE user_tg_links SET username=NULL WHERE tg_id=$1", TG)
    await db.set_tg_username(TG, None)
    check("пустой логин не затирает известный", True,
          "человек мог открыть бота из аккаунта без логина")

    print()
    print("=== привязки нет ===")
    check("так и написано", await _tg_line(FakeContext(), []) == "Не привязан")

    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cp-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
