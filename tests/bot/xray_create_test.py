# -*- coding: utf-8 -*-
"""Выдача нового ключа: протокол по умолчанию, ссылка и инструкция."""
import asyncio
import json

from database import db
import xray
import handlers_xray as hx
from handlers_users import new_key_screen


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


class FakeSession:
    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV", "password": "PUB"})
        return FakeResp({"status": "ok", "note": "запущен"})

    def get(self, url, timeout=None):
        return FakeResp([], 200)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeBot:
    def __init__(self):
        self.messages = []
        self.photos = []
        self.captions = []

    async def send_message(self, chat_id, text, **kw):
        self.messages.append((chat_id, text))

    async def send_photo(self, chat_id, photo, **kw):
        # Подпись тоже нужна: предупреждение о личной ссылке живёт
        # в ней, а не отдельным сообщением.
        self.photos.append(chat_id)
        self.captions.append((chat_id, kw.get("caption") or ""))

    async def send_document(self, chat_id, document, **kw):
        self.messages.append((chat_id, "document"))


class FakeContext:
    def __init__(self):
        self.bot = FakeBot()
        self.user_data = {}


class FakeUpdate:
    effective_chat = type("C", (), {"id": 100})()


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cr-%'")
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                     "Ника", "cr-1")
    await db.set_setting("server_host", "203.0.113.9")

    xray.api_session = lambda: FakeSession()

    async def ips():
        return {"cr-1": "10.13.13.6"}
    xray.peer_ip_map = ips

    ctx = FakeContext()

    print("=== экран нового ключа ===")
    text, kb = await new_key_screen(ctx, "Ника")
    buttons = [b.callback_data for row in kb.inline_keyboard for b in row]
    print([b.text for row in kb.inline_keyboard for b in row])
    assert "Xray" in text and "new_proto" in buttons
    assert "set_exp_30" in buttons, buttons
    print("по умолчанию Xray, срок на месте: ок")

    ctx.user_data["proto"] = "awg"
    text, kb = await new_key_screen(ctx, "Ника")
    assert "AmneziaWG" in text and "роутер" in text
    print("переключение на AmneziaWG объясняет, кому он нужен: ок")

    print("\n=== пока Xray выключен, по умолчанию AmneziaWG ===")
    from handlers_users import default_proto

    async def off():
        return {"awg": {"enabled": True}, "xray": {"enabled": False}}
    xray.status = off
    assert await default_proto() == "awg",         "ссылка на выключенный протокол выглядит рабочей, но молчит"

    async def on():
        return {"awg": {"enabled": True}, "xray": {"enabled": True}}
    xray.status = on
    assert await default_proto() == "xray"

    async def dead():
        raise RuntimeError("узел молчит")
    xray.status = dead
    assert await default_proto() == "awg", "при молчании узла — то, что точно работает"
    xray.status = on
    print("выключенный протокол не предлагается: ок")

    print("\n=== инструкция сразу со ссылками ===")
    ins = await hx.instructions()
    for line in ins.split("\n")[:6]:
        print(" ", line)
    assert "Happ" in ins, ins
    # Ссылки должны быть настоящими и оформленными подписью: голый адрес
    # Telegram ломает на знаках, которые принимает за разметку.
    assert "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215" in ins
    assert "https://play.google.com/store/apps/details?id=com.happproxy" in ins
    assert "[App Store](" in ins and "[Google Play](" in ins
    assert "не передавайте" in ins
    print("приложение названо, ссылки на месте: ок")

    print("\n=== человек выбирает свою систему ===")
    import handlers_xray as _hx
    kb = _hx.platform_keyboard("cr-1")
    labels = [b.text for row in kb.inline_keyboard for b in row]
    codes = [b.callback_data for row in kb.inline_keyboard for b in row]
    print(" ", labels)
    assert "iPhone / iPad" in labels and "Android" in labels
    assert "client_plat_ios_cr-1" in codes, codes
    # 64 байта — предел Telegram на подпись кнопки
    assert all(len(c.encode()) <= 64 for c in codes), codes

    one = await _hx.instructions("cr-1", "android")
    print(" ", one.split(chr(10))[2][:90])
    assert "Android" in one and "Google Play" in one
    assert "iPhone" not in one, "человеку не нужны чужие системы"
    print("инструкция приходит под его систему: ок")


    print("\n=== выдача ссылки ===")
    ok = await hx.handout(FakeUpdate(), ctx, "cr-1", "Ника", tg_id=555)
    assert ok
    to_admin = [m for m in ctx.bot.messages if m[0] == 100]
    to_user = [m for m in ctx.bot.messages if m[0] == 555]
    print("владельцу сообщений:", len(to_admin), "· человеку:", len(to_user))
    assert any("vless://" in m[1] for m in to_admin), "владельцу ссылка не ушла"
    assert any("vless://" in m[1] for m in to_user), "человеку ссылка не ушла"
    assert 555 in ctx.bot.photos, "QR человеку не ушёл"
    # Предупреждение — подписью к картинке, третьего сообщения нет.
    caps = [c for c in ctx.bot.captions if c[0] == 555]
    assert any("не передавайте" in c[1] for c in caps), caps
    print("ссылка, QR и предупреждение доехали: ок")

    rec = await db.get_xray_user("cr-1")
    assert rec and rec["sub_token"]
    print("подключение записано в базу: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'cr-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
