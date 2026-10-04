# -*- coding: utf-8 -*-
"""Поиск масок из бота: выбрал устройство → узел нашёл имена → добавил в группу.

Маски сами по себе непонятны: приложение не говорит, под какой сайт прячется.
Поиск должен показать только новые имена (те, что уже в группе, повторять
незачем), а «Добавить» — положить их в группу масками и применить на узле.
"""
import asyncio
import time

from database import db
import filters

KEY = "pool_tmask_dd44"


class Resp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class Session:
    def get(self, url, **kw):
        now = int(time.time())
        return Resp([{"uuid": "tm-1", "latest_handshake": now - 10,
                      "allowed_ips": "10.13.13.8/32"},
                     {"uuid": "tm-2", "latest_handshake": now - 4000,
                      "allowed_ips": "10.13.13.9/32"}])

    def post(self, url, json=None, **kw):
        SENT.append((url, json))
        return Resp({"status": "ok", "candidates": [
            {"name": "nalog.ru", "hits": 7, "ports": [21278]},
            {"name": "moedelo.org", "hits": 3, "ports": [12039, 12202]}]})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


SENT = []


class Msg:
    chat_id = 4242
    message_id = 1
    photo = None
    document = None


class Query:
    def __init__(self):
        self.message = Msg()
        self.texts = []
        self.kb = None
        self.answers = []

    async def edit_message_text(self, text, reply_markup=None, **kw):
        self.texts.append(text)
        self.kb = reply_markup

    async def answer(self, *a, **k):
        self.answers.append(a[0] if a else "")


class Upd:
    def __init__(self, q):
        self.callback_query = q


class Ctx:
    def __init__(self):
        self.user_data = {}


def buttons(q):
    return [b.callback_data for row in q.kb.inline_keyboard for b in row]


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'tm-%'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('Телефон', 'tm-1'), "
                     "('Спящий', 'tm-2')")
    await db.save_filter_pool(KEY, "Проверка", ["likee.video", "маска:nalog.ru"])
    filters.api_session = lambda **k: Session()
    applied = []

    async def fake_apply(reason=""):
        applied.append(reason)
        return True, "ок"
    filters.apply_filters = fake_apply
    filters.MASK_SNIFF_SECONDS = 1

    print("=== кнопка на экране группы ===")
    q, c = Query(), Ctx()
    await filters.pool_open(Upd(q), c, KEY)
    assert "flt_pool_m_" + KEY in buttons(q)
    assert "маски" in q.texts[-1].lower()
    print("  «Найти маски» есть, что такое маска — сказано: ок")

    print("\n=== выбор устройства: только те, кто на связи ===")
    q = Query()
    await filters.pool_mask_pick(Upd(q), c, KEY)
    assert buttons(q)[0] == "flt_pm_0" and len([b for b in buttons(q) if b.startswith("flt_pm_")]) == 1
    print("  предложен «Телефон», спящий — нет: ок")

    print("\n=== поиск: показываются только новые имена ===")
    q = Query()
    await filters.pool_mask_run(Upd(q), c, 0)
    url, body = SENT[-1]
    assert url.endswith("/dns/sniff") and body["ip"] == "10.13.13.8", SENT[-1]
    text = q.texts[-1]
    assert "moedelo.org" in text and "nalog.ru" not in text, text
    assert "flt_pmadd" in buttons(q)
    print("  узел спрошен по адресу телефона; nalog.ru уже в группе — не повторён: ок")

    print("\n=== добавить ===")
    q = Query()
    await filters.pool_mask_add(Upd(q), c)
    doms = (await db.get_filter_pool(KEY))["domains"]
    assert "маска:moedelo.org" in doms and "маска:nalog.ru" in doms, doms
    assert applied and "маски" in applied[-1]
    print("  маска в группе, применено на узле: ок")

    await db.delete_filter_pool(KEY)
    await db.execute("DELETE FROM users WHERE uuid LIKE 'tm-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
