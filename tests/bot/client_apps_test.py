# -*- coding: utf-8 -*-
"""Человек видит, откуда ставить приложение — без лишних нажатий.

Владелец не нашёл у людей перечня ссылок на приложения. И правильно: экран
«Как подключить» показывал одну строку «выберите свою систему» и кнопки. Ни
одной ссылки на нём не было — чтобы увидеть, куда идти, надо было угадать, что
за кнопкой платформы что-то есть, и нажать ещё раз.

Проверяется то, что человек реально получает:
  • на первом же экране есть ссылки на все системы;
  • ни одна система не забыта — человек с макбуком не должен остаться ни с чем;
  • кнопки платформ остались: они сокращают список, когда система уже известна;
  • выбрав систему, человек видит свою строку, а не всё подряд.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import handlers_xray as hx                         # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeQuery:
    from_user = type("U", (), {"id": 1})()

    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard if reply_markup else [])
                            for b in row]

    async def answer(self, *a, **k):
        return None


class FakeUpdate:
    callback_query = FakeQuery()
    effective_chat = type("C", (), {"id": 1})()


TG = 987654321


class MenuUpdate:
    """Меню смотрит на того, кто нажал: по нему находятся ключи человека."""
    callback_query = FakeQuery()
    effective_chat = type("C", (), {"id": TG})()
    effective_user = type("U", (), {"id": TG, "first_name": "Приложенцев"})()


class MenuBot:
    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard if reply_markup else [])
                            for b in row]


class MenuContext:
    bot = MenuBot()
    user_data = {}


async def main():
    await db.connect()
    import handlers_client as hc

    print("=== первый экран «Как подключить» ===")
    await hc.client_how_handler(FakeUpdate(), None, "any-uuid")
    text = shown.get("text") or ""
    print("  строк на экране:", len(text.split(chr(10))))

    check("ссылки есть прямо здесь", "http" in text,
          "раньше их не было вовсе")
    check("приложение названо", "Happ" in text)

    for system in ("iPhone", "Android", "Windows", "macOS", "Linux"):
        check("есть %s" % system, system in text)

    check("кнопки систем остались", len(shown.get("buttons") or []) >= 5,
          "кнопок: %d" % len(shown.get("buttons") or []))
    check("есть выход назад",
          any("client_key_manage" in b for b in shown.get("buttons") or []))

    print()
    print("=== выбрал систему — видит свою строку ===")
    await hc.client_platform_handler(FakeUpdate(), None, "android", "any-uuid")
    one = shown.get("text") or ""
    check("его система на месте", "Android" in one)
    check("ссылка на месте", "http" in one)
    check("список стал короче общего", len(one) < len(text),
          "%d против %d знаков" % (len(one), len(text)))
    check("можно вернуться к списку систем",
          any("client_how" in b for b in shown.get("buttons") or []))


    print()
    print("=== путь из личного кабинета ===")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ap-%'")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Приложенцев','ap-1',TRUE)")
    await db.execute(
        "INSERT INTO user_tg_links (uuid, tg_id) VALUES ('ap-1',$1)", TG)

    # Одно меню перерисовывает текущее сообщение, другое шлёт новое, и зовут их
    # по-разному: первое — по нажатию, второе — когда бот пишет сам.
    views = ((lambda: hc.client_menu(MenuUpdate(), MenuContext()), "перерисованное меню"),
             (lambda: hc.send_client_menu(MenuContext(), TG, "Приложенцев"), "отправленное меню"))
    for view, label in views:
        shown.clear()
        await view()
        buttons = shown.get("buttons") or []
        check("%s: кнопка приложений" % label, "client_apps" in buttons,
              ", ".join(buttons))
        check("%s: «что нового» на месте" % label,
              "client_whats_new" in buttons,
              "кнопка, которая то есть, то нет, читается как поломка")

    print()
    print("=== экран приложений показывает нужную программу ===")
    shown.clear()
    await hc.client_apps_handler(MenuUpdate(), MenuContext())
    text = shown.get("text") or ""
    check("ключ по AmneziaWG — своё приложение", "AmneziaWG" in text)
    check("чужого приложения нет", "Happ" not in text,
          "у человека нет ссылки vless://")

    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('ap-1','x-ap','tok-ap')")
    shown.clear()
    await hc.client_apps_handler(MenuUpdate(), MenuContext())
    text = shown.get("text") or ""
    check("ключ по Xray — Happ", "Happ" in text)
    for system in ("iPhone", "Android", "Windows", "macOS", "Linux"):
        check("есть %s" % system, system in text)
    check("есть выход в кабинет",
          "client_menu" in (shown.get("buttons") or []))

    await db.execute("DELETE FROM xray_users WHERE user_uuid LIKE 'ap-%'")
    await db.execute("DELETE FROM user_tg_links WHERE tg_id=$1", TG)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ap-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
