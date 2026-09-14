# -*- coding: utf-8 -*-
"""По ссылке можно нажать, а не только выделять и копировать.

Владелец спросил, нельзя ли сделать ссылку нажимаемой, чтобы открывалось
приложение. Можно: схему `vless://` Telegram принимает и в тексте, и в кнопке —
проверено прямым запросом к его API, разбор проходит, ошибка приходит только
про несуществующий чат. Кириллица в хвосте ссылки (имя человека) тоже проходит.

Но кнопка — не замена ссылке. Если приложение не установлено, нажатие приведёт
в никуда, и человеку останется только скопировать текст. Поэтому проверяем не
«кнопка есть», а «кнопка есть И ссылка осталась текстом».
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import xray                                        # noqa: E402

ok = True
sent = []


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeBot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        sent.append({"text": text, "markup": reply_markup})

    async def send_photo(self, **kw):
        sent.append({"photo": True})


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'bt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'bt-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Ссылкин','bt-1',TRUE)")
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('bt-1','x-1','tok-1')")
    for key, val in (("xray_public_key", "PUB"), ("xray_short_id", "ab"),
                     ("server_host", "1.2.3.4")):
        await db.set_setting(key, val)

    link = await xray.profile_link("bt-1")
    print("=== сама ссылка ===")
    check("собралась", bool(link))
    check("имя человека в хвосте — кириллицей",
          link.endswith("Ссылкин"), link[-12:])

    print()
    print("=== клавиатура к ссылке ===")
    kb = xray.link_keyboard(link, ("🏠 Личный кабинет", "client_menu"))
    buttons = [b for row in kb.inline_keyboard for b in row]
    opener = [b for b in buttons if getattr(b, "url", None)]
    check("есть кнопка со ссылкой", len(opener) == 1,
          opener[0].text if opener else "нет")
    check("кнопка ведёт ровно на эту ссылку",
          opener and opener[0].url == link)
    check("выход рядом есть",
          any(getattr(b, "callback_data", None) == "client_menu" for b in buttons))

    print()
    print("=== ссылка при этом осталась текстом ===")
    import handlers_client as hc
    sent.clear()
    await hc.send_xray_profile(FakeContext(), 1, "bt-1")
    texts = [m.get("text") for m in sent if m.get("text")]
    check("ссылка ушла отдельным сообщением", link in texts,
          "иначе её нельзя скопировать, если приложения нет")
    with_button = [m for m in sent
                   if m.get("markup") and any(getattr(b, "url", None)
                                              for row in m["markup"].inline_keyboard
                                              for b in row)]
    check("и у него есть кнопка", len(with_button) >= 1)

    print()
    print("=== предупреждение о личной ссылке на месте ===")
    check("сказано не передавать",
          any("не передавайте" in (x or "") for x in texts))

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'bt-%'")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'bt-%'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
