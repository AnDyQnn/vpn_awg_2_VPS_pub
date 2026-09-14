# -*- coding: utf-8 -*-
"""Число на кнопке «Администрирование» обязано объяснять себя.

Владелец: «на главном меню написано, что ждут 3, перехожу в администрирование —
и там ничего нету, куда топать, чо смотреть, хуй поймёшь».

Так и было: счётчик складывал пять источников в одном месте, а экран собирал
те же данные заново и показывал их прозой, вразнобой. Связи между числом и
разделами не было никакой.

Проверяется:
  • разбор и число берутся из одного места и всегда сходятся — две копии
    величины расходятся молча, это уже было с потолком узла;
  • на экране видно, из чего именно сложилось число;
  • на каждое есть кнопка, и она ведёт на существующий экран;
  • когда ждать нечего — блока нет вовсе, а не «ждёт внимания: 0».
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import handlers_service as hs                      # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-48s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class FakeQuery:
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
    await db.execute("DELETE FROM users WHERE uuid LIKE 'aw-%'")
    await db.execute("DELETE FROM support_tickets")
    await db.execute("DELETE FROM pending_decisions")

    print("=== ждать нечего ===")
    items = await hs.admin_waiting()
    total = await hs.admin_counter()
    check("разбор пуст", items == [], str(items))
    check("число ноль", total == 0, total)
    await hs.service_menu(FakeUpdate(), None)
    check("блока «ждёт внимания» нет", "Ждёт внимания" not in shown["text"],
          "ноль показывать незачем")

    print()
    print("=== появились дела ===")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ('Ждун','aw-1',TRUE)")
    await db.execute(
        "INSERT INTO support_tickets (user_uuid, message, status) "
        "VALUES ('aw-1','не работает','open')")
    await db.execute(
        "INSERT INTO pending_decisions (user_uuid, reason) VALUES ('aw-1','expired')")

    items = await hs.admin_waiting()
    total = await hs.admin_counter()
    print("  разбор:", [(t, n) for t, n, _ in items])
    check("число сходится с разбором", total == sum(n for _t, n, _g in items),
          "%d = %s" % (total, "+".join(str(n) for _t, n, _g in items)))
    check("обращение учтено", any("поддержк" in t for t, _n, _g in items))
    check("решение учтено", any("решени" in t for t, _n, _g in items))

    print()
    print("=== экран объясняет число ===")
    await hs.service_menu(FakeUpdate(), None)
    text = shown["text"]
    check("блок есть", "Ждёт внимания" in text)
    check("названо число", f"Ждёт внимания: {total}" in text,
          re.search(r"Ждёт внимания: \d+", text).group(0) if "Ждёт" in text else "—")
    for title, _n, _g in items:
        check("строка «%s»" % title, title in text)

    print()
    print("=== на каждое есть кнопка ===")
    buttons = shown["buttons"]
    for _title, _n, target in items:
        check("кнопка ведёт в %s" % target, target in buttons)
    check("кнопок не больше, чем дел", len(set(b for b in buttons)) >= len(items))

    await db.execute("DELETE FROM support_tickets")
    await db.execute("DELETE FROM pending_decisions")
    await db.execute("DELETE FROM users WHERE uuid LIKE 'aw-%'")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
