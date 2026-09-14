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


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
