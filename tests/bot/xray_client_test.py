# -*- coding: utf-8 -*-
"""Личный кабинет: за теми же кнопками — то, что подходит протоколу."""
import asyncio
import json

from database import db
import xray
import handlers_client as hc


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


sent = {"messages": [], "photos": [], "documents": [], "screen": None,
        "markup": None}


class FakeBot:
    async def send_message(self, chat_id, text, **kw):
        sent["messages"].append(text)

    async def send_photo(self, chat_id, photo, **kw):
        sent["photos"].append(kw.get("caption", ""))

    async def send_document(self, chat_id, document, **kw):
        sent["documents"].append(kw.get("caption", ""))


class FakeMessage:
    chat_id = 100

    async def reply_text(self, text, **kw):
        sent["messages"].append(text)


class FakeQuery:
    message = FakeMessage()

    async def answer(self, text="", show_alert=False):
        pass

    async def edit_message_text(self, text, reply_markup=None, **kw):
        sent["screen"] = text
        sent["markup"] = [b.text for row in (reply_markup.inline_keyboard
                                             if reply_markup else []) for b in row]


class FakeUpdate:
    callback_query = FakeQuery()


class FakeContext:
    bot = FakeBot()


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cl-%'")
    for uid, name in (("cl-1", "НаXray"), ("cl-2", "НаAmnezia")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    xray.api_session = lambda: FakeSession()

    async def ips():
        return {"cl-1": "10.13.13.6", "cl-2": "10.13.13.7"}
    xray.peer_ip_map = ips
    await db.set_setting("server_host", "203.0.113.9")

    async def live():
        return {}
    hc.get_live_peers_status = live

    ok, token = await xray.issue("cl-1")
    assert ok

    upd, ctx = FakeUpdate(), FakeContext()

    print("=== карточка ключа у человека на Xray ===")
    await hc.client_key_manage_handler(upd, ctx, "cl-1")
    print(sent["markup"])
    assert "📥 Получить ссылку" in sent["markup"]
    assert "❓ Как подключить" in sent["markup"]
    assert "новую ссылку" in sent["screen"], sent["screen"]
    print("кнопки те же, подписи по делу: ок")

    print("\n=== карточка у человека на AmneziaWG ===")
    await hc.client_key_manage_handler(upd, ctx, "cl-2")
    print(sent["markup"])
    assert "📥 Скачать конфиг" in sent["markup"]
    assert "❓ Как подключить" not in sent["markup"]
    print("ничего не изменилось: ок")

    print("\n=== «скачать» отдаёт ссылку, а не файл ===")
    sent["messages"], sent["photos"], sent["documents"] = [], [], []
    await hc.client_download_handler(upd, ctx, "cl-1")
    print("сообщений:", len(sent["messages"]), "· QR:", len(sent["photos"]),
          "· файлов:", len(sent["documents"]))
    # Человеку уходит один адрес — подписка. Разовая ссылка осталась у
    # владельца: человеку нужен один способ подключиться, а не три.
    assert any("vless://" in m for m in sent["messages"]), sent["messages"]
    assert not sent["documents"], "человеку на Xray прислали файл конфига"
    # Предупреждение — подписью к картинке, чтобы не плодить третье сообщение.
    assert any("не передавайте" in (m or "")
               for m in sent["messages"] + sent["photos"]), sent["photos"]
    print("ссылка, QR и предупреждение: ок")

    print("\n=== «на связи» по трафику двойника ===")
    import time
    from utils import state_data
    state_data["addr_seen"]["10.13.13.134"] = time.time()
    await hc.client_key_manage_handler(upd, ctx, "cl-1")
    assert "На связи" in sent["screen"], sent["screen"]
    print("виден онлайн без рукопожатия: ок")

    print("\n=== перевыпуск объясняет, что будет ===")
    await hc.client_regen_confirm(upd, ctx, "cl-1")
    assert "прежняя перестанет работать сразу" in sent["screen"], sent["screen"]
    await hc.client_regen_confirm(upd, ctx, "cl-2")
    assert "файл конфигурации" in sent["screen"], sent["screen"]
    print("для каждого свой текст: ок")

    print("\n=== перевыпуск меняет ссылку ===")
    sent["messages"], sent["photos"] = [], []
    await hc.client_regen_action(upd, ctx, "cl-1")
    rec = await db.get_xray_user("cl-1")
    assert rec["sub_token"] != token, "токен не сменился"
    assert await xray.subscription_body(token) == "", "старая ссылка ещё жива"
    # Человеку уходит один адрес — подписка. Разовая ссылка осталась
    # у владельца: человеку нужен один способ подключиться, а не три.
    assert any("vless://" in m for m in sent["messages"]), sent["messages"]
    print("новая ссылка выдана, старая мертва: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'cl-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
