# -*- coding: utf-8 -*-
"""Общие правила и свой список сайтов — от экрана до раскладки на узел.

Проверяется весь путь: нажатие на экране → настройка в базе → то, что уедет
узлу. Отдельно проверяется разбор адреса: человек пришлёт ссылку целиком, а
не голый домен.
"""
import asyncio
import json

from database import db
import filters as F


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def text(self):
        return json.dumps(self._p)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


sent = {}


class FakeSession:
    def post(self, url, json=None, timeout=None):
        sent.update(json)
        return FakeResp({"filtered": len(json.get("clients") or {})})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


shown = {}


async def fake_show(query, context, text, reply_markup=None, parse_mode=None,
                    disable_preview=False):
    shown["text"] = text
    shown["buttons"] = [b.callback_data for row in
                        (reply_markup.inline_keyboard if reply_markup else [])
                        for b in row]
    shown["labels"] = [b.text for row in
                       (reply_markup.inline_keyboard if reply_markup else [])
                       for b in row]


class FakeQuery:
    message = type("M", (), {"chat_id": 1, "message_id": 2})()

    async def answer(self, text="", show_alert=False):
        shown.setdefault("answers", []).append(text)


class FakeUpdate:
    callback_query = FakeQuery()
    effective_chat = type("C", (), {"id": 1})()
    message = type("Msg", (), {"text": "", "chat_id": 1})()


class FakeContext:
    user_data = {}
    bot = type("B", (), {"send_message": staticmethod(
        lambda **kw: asyncio.sleep(0, result=shown.setdefault(
            "messages", []).append(kw.get("text", ""))))})()


async def main():
    await db.connect()
    await db.execute("DELETE FROM settings WHERE key LIKE 'filters_%'")

    F.api_session = lambda: FakeSession()
    F.show_screen = fake_show

    async def no_addrs():
        return {}
    F.peer_addr_map = no_addrs

    upd, ctx = FakeUpdate(), FakeContext()

    print("=== разбор того, что пришлёт человек ===")
    for raw, expect in (("https://yandex.ru", "yandex.ru"),
                        ("www.Example.COM/path?x=1", "example.com"),
                        ("  vk.com  ", "vk.com"),
                        ("сайт.рф", "сайт.рф")):
        got, err = F.parse_site(raw)
        print(f"  {raw!r:28} → {got}")
        assert got == expect and not err, (raw, got, err)
    for bad in ("", "просто слово", "http://"):
        got, err = F.parse_site(bad)
        assert err and not got, (bad, got)
    print("ссылка, домен и мусор различаются: ок")

    print("\n=== экран общих правил ===")
    await F.common_screen(upd, ctx)
    print(" ", shown["labels"][:3], "…")
    assert "flt_cadd" in shown["buttons"], shown["buttons"]
    assert any(b.startswith("flt_ctog_") for b in shown["buttons"])
    assert "Категории не выбраны" in shown["text"]
    print("пусто и предлагает закрыть: ок")

    print("\n=== включаем категорию для всех ===")
    key = F.CATEGORIES[0][0]
    await F.common_toggle(upd, ctx, key)
    assert await db.get_common_filters() == [key], await db.get_common_filters()
    print(" ", "узлу ушло:", sent.get("common"))
    assert sent["common"] == [key], sent
    print("категория уехала на узел: ок")

    print("\n=== закрываем конкретный сайт ссылкой ===")
    upd.message.text = "https://yandex.ru/maps"
    await F.custom_add_entered(upd, ctx, upd.message.text)
    assert await db.get_custom_blocks() == ["yandex.ru"], await db.get_custom_blocks()
    print(" ", "узлу ушло:", sent.get("custom"))
    assert sent["custom"] == ["yandex.ru"], sent
    print("из ссылки достался домен и уехал: ок")

    print("\n=== снятие запрета ===")
    await F.custom_remove(upd, ctx, "yandex.ru")
    assert await db.get_custom_blocks() == []
    assert sent["custom"] == [], sent
    print("список пуст, узел знает: ок")

    print("\n=== выключение категории ===")
    await F.common_toggle(upd, ctx, key)
    assert await db.get_common_filters() == []
    assert sent["common"] == [], sent
    print("общих правил не осталось: ок")

    await db.execute("DELETE FROM settings WHERE key LIKE 'filters_%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
