# -*- coding: utf-8 -*-
"""Экраны протоколов: что человек и владелец видят на самом деле."""
import asyncio
import json
import time

from database import db
import xray
import handlers_xray as hx


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


PEERS = [{"uuid": "sc-1", "allowed_ips": "10.13.13.6/32",
          "latest_handshake": int(time.time()) - 30},
         {"uuid": "sc-2", "allowed_ips": "10.13.13.7/32", "latest_handshake": 0}]


class FakeSession:
    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV", "password": "PUB"})
        return FakeResp({"status": "ok", "note": "запущен"})

    def get(self, url, timeout=None):
        if url.endswith("/peers"):
            return FakeResp(PEERS)
        return FakeResp({}, 404)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


shown = {}


async def fake_show(query, context, text, reply_markup=None, parse_mode=None,
                    disable_preview=False):
    shown["text"] = text
    shown["buttons"] = [b.callback_data for row in (reply_markup.inline_keyboard
                                                    if reply_markup else [])
                        for b in row]
    shown["labels"] = [b.text for row in (reply_markup.inline_keyboard
                                          if reply_markup else []) for b in row]


class FakeQuery:
    def __init__(self):
        self.answers = []
        self.message = type("M", (), {"chat_id": 1, "message_id": 2})()

    async def answer(self, text="", show_alert=False):
        self.answers.append(text)


class FakeUpdate:
    def __init__(self):
        self.callback_query = FakeQuery()


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sc-%'")
    for uid, name in (("sc-1", "Ника"), ("sc-2", "Папа")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    xray.api_session = lambda: FakeSession()
    hx.show_screen = fake_show

    async def ips():
        return {"sc-1": "10.13.13.6", "sc-2": "10.13.13.7"}
    xray.peer_ip_map = ips

    async def status():
        return {"awg": {"enabled": True, "up": True, "peers": 2},
                "xray": {"enabled": True, "up": True, "connections": 3,
                         "has_config": True}}
    xray.status = status

    upd = FakeUpdate()

    print("=== блок подключений в карточке ===")
    st = await xray.person_state("sc-1")
    block = hx.connections_block(st)
    print(block)
    assert "AmneziaWG" in block and "Xray — не выдан" in block
    print("до выдачи: ок")

    ok, _ = await xray.issue("sc-1")
    assert ok
    st = await xray.person_state("sc-1")
    block = hx.connections_block(st)
    print(block)
    assert "ни разу не подключался" in block, block
    print("после выдачи: ок")

    from utils import state_data
    state_data["addr_seen"]["10.13.13.134"] = time.time()
    st = await xray.person_state("sc-1")
    assert "Xray — на связи" in hx.connections_block(st)
    print("трафик по двойнику = человек на связи: ок")

    print("\n=== экран подключений ===")
    await hx.connections_screen(upd, None, "sc-1")
    print(shown["labels"])
    assert "xr_send_sc-1" in shown["buttons"]
    assert "xr_issue_sc-1" in shown["buttons"]
    # пир есть, живого подключения по Xray ещё не было → кнопка заперта
    assert "xr_why_sc-1" in shown["buttons"], shown["buttons"]
    assert "xr_dropawg_sc-1" not in shown["buttons"]
    print("снять AmneziaWG нельзя, пока человек не переехал: ок")

    await db.mark_xray_seen("sc-1")
    await hx.connections_screen(upd, None, "sc-1")
    assert "xr_dropawg_sc-1" in shown["buttons"], shown["buttons"]
    print("после живого подключения кнопка открылась: ок")

    print("\n=== экран протоколов ===")
    await hx.protocols_menu(upd, None)
    print(shown["text"])
    assert "AmneziaWG" in shown["text"] and "Xray" in shown["text"]
    assert set(shown["buttons"]) >= {"proto_awg", "proto_xray", "xr_move"}
    print("оба протокола и перевод: ок")

    print("\n=== выключение спрашивает, кого оборвёт ===")
    await hx.switch_confirm(upd, None, "awg")
    print(shown["text"].replace("\n", " ")[:120])
    assert "оборвётся" in shown["text"] and "proto_offok_awg" in shown["buttons"]
    await hx.switch_confirm(upd, None, "xray")
    assert "proto_offok_xray" in shown["buttons"]
    print("подтверждение с последствиями: ок")

    print("\n=== экран приложений показывает то же, что увидит человек ===")
    await hx.apps_screen(upd, None)
    print(shown["text"].split("\n")[4])
    assert "Happ" in shown["text"]
    assert "https://play.google.com/store/apps/details?id=com.happproxy" in shown["text"]
    # Платформы должны быть все: человек с макбуком не должен остаться ни с чем.
    for platform in ("iPhone", "Android", "Windows", "macOS", "Linux"):
        assert platform in shown["text"], platform
    assert shown["buttons"] == ["proto_xray"], shown["buttons"]
    print("все системы и ссылки на месте: ок")

    print("\n=== перевод людей ===")
    await hx.move_screen(upd, None)
    print(shown["text"].split("\n")[2:5])
    assert "Переехали: **1**" in shown["text"], shown["text"]
    assert "Не выдавали: **1**" in shown["text"], shown["text"]
    print("считает по живому подключению, а не по выдаче: ок")

    print("\n=== экран Xray ===")
    await hx.xray_screen(upd, None)
    assert "адрес не задан" in shown["text"], shown["text"]
    assert "xr_apply" in shown["buttons"] and "proto_off_xray" in shown["buttons"]
    print("предупреждает, что автообновление выключено: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'sc-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
