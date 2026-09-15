# -*- coding: utf-8 -*-
"""Список копий: когда сделана, целая ли, зашифрована ли.

Кнопки «сделать копию» и «восстановить» были, а посмотреть, что уже лежит на
сервере, было негде. Отсюда и путаница в аудите: он писал «бэкап не найден»,
строкой выше — «файлов бэкапов: 6», и разобраться можно было только зайдя на
узел руками.

Проверка целостности архива в проекте была написана давно, но её никто не звал:
о сломанной копии узнавали в тот момент, когда она понадобилась.
"""
import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "/app")

import handlers_admin as ha                        # noqa: E402
import backup_manager                              # noqa: E402

ok = True
shown = {}


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Q:
    async def edit_message_text(self, text=None, reply_markup=None, **kw):
        shown["text"] = text
        shown["buttons"] = [b.callback_data
                            for row in (reply_markup.inline_keyboard
                                        if reply_markup else [])
                            for b in row]

    async def answer(self, *a, **k):
        return None


class U:
    callback_query = Q()
    effective_chat = type("C", (), {"id": 1})()


class Ctx:
    user_data = {}


async def main():
    print("=== копий нет ===")
    backup_manager.list_backups = lambda: []
    ha.list_backups = backup_manager.list_backups
    shown.clear()
    await ha.backups_list_screen(U(), Ctx())
    check("сказано прямо", "не нашлось" in (shown.get("text") or ""),
          "пустой экран человек читает как поломку")
    check("есть чем это исправить",
          "backup" in (shown.get("buttons") or []))

    print()
    print("=== копии есть, одна битая ===")
    items = [
        {"name": "backup_20260915_130712_pc2687ce1.tar.gz.gpg", "size_mb": 1.21,
         "when": datetime(2026, 9, 15, 13, 7), "ok": True, "note": ""},
        {"name": "backup_20260914_080013.tar.gz", "size_mb": 0.02,
         "when": datetime(2026, 9, 14, 8, 0), "ok": False,
         "note": "архив не открывается"},
    ]
    backup_manager.list_backups = lambda: items
    shown.clear()
    await ha.backups_list_screen(U(), Ctx())
    text = shown.get("text") or ""
    check("посчитаны все", "Всего: **2**" in text, text[:60])
    check("и отдельно целые", "целых: **1**" in text)
    check("битая помечена", "⚠️" in text)
    check("сказано, что с ней не так", "не открывается" in text,
          "иначе про неё узнают, когда она понадобится")
    check("видно время", "15.09" in text)

    print()
    print("=== пароль архива не задан ===")
    backup_manager.BACKUP_PASSWORD = ""
    shown.clear()
    await ha.backups_list_screen(U(), Ctx())
    check("предупреждение показано",
          "незашифрован" in (shown.get("text") or ""),
          "копия — это ключ сервера и конфиги всех людей")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
