# -*- coding: utf-8 -*-
"""Доступы по именам — через экраны бота, а не мимо них.

Проверяется весь путь: нажатие кнопки на экране роли → запись в базу →
раскладка, которая уедет узлу. Payload сохраняется на диск, чтобы узловой
тест применил РОВНО его, а не придуманный руками, — иначе проверялся бы код,
а не стык между ботом и узлом.
"""
import asyncio
import json
import os

from database import db
import acl
import dnsnames as dn
import handlers_roles as hr

PAYLOAD_OUT = "/out/acl_payload.json"

sent = {}


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
    """Ловит то, что бот отправляет узлу. Ответ — как у настоящего узла."""

    def post(self, url, json=None, timeout=None):
        sent[url.rsplit("/", 1)[-1]] = json
        if url.endswith("/acl"):
            peers = json.get("peers", [])
            rules = sum(len(p.get("allow", [])) for p in peers)
            return FakeResp({"status": "ok", "peers": len(peers), "rules": rules})
        return FakeResp({"status": "ok"})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeQuery:
    def __init__(self):
        self.alerts = []
        self.message = type("M", (), {"chat_id": 1, "message_id": 2})()

    async def answer(self, text="", show_alert=False):
        self.alerts.append(text)


class FakeUpdate:
    def __init__(self):
        self.callback_query = FakeQuery()
        self.effective_chat = type("C", (), {"id": 1})()


class FakeContext:
    def __init__(self):
        self.user_data = {}
        self.bot = type("B", (), {
            "send_message": staticmethod(
                lambda **kw: asyncio.sleep(0, result=None))})()


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


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rn-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'тест-%'")
    # Имена от соседних тестов мешают: экран показывает их все, и порядок
    # кнопок перестаёт быть предсказуемым.
    await db.execute("DELETE FROM dns_names")
    for uid, name in (("rn-1", "Ника"), ("rn-2", "ДомашнийСервер")):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)

    acl.api_session = lambda: FakeSession()
    dn.api_session = lambda: FakeSession()
    hr.show_screen = fake_show

    async def ips():
        return {"rn-1": "10.13.13.20", "rn-2": "10.13.13.21"}
    acl.peer_ip_map = ips
    hr.peer_ip_map = ips

    print("=== заводим имя домашнему серверу ===")
    name, err = dn.normalize("дом")
    assert not err, err
    await db.set_dns_name(name, target_uuid="rn-2")
    await dn.apply_names("тест")
    print(" ", name, "→", (await dn.resolve_all())[0][name])

    print("\n=== экран доступов предлагает имя кнопкой ===")
    role_id = await db.create_role("тест-роль")
    upd, ctx = FakeUpdate(), FakeContext()
    await hr.grant_add_screen(upd, ctx, role_id)
    print(" ", shown["labels"][:3])
    assert f"role_gname_{role_id}_{name}" in shown["buttons"], shown["buttons"]
    # Важна группа, а не место: имён может быть много, и порядок между ними
    # неважен. Важно, что все они выше адресов.
    last_name = max(i for i, b in enumerate(shown["buttons"])
                    if b.startswith("role_gname_"))
    first_peer = min((i for i, b in enumerate(shown["buttons"])
                      if b.startswith("role_gpeer_")), default=10 ** 6)
    assert last_name < first_peer, shown["buttons"]
    print("имена идут выше адресов: ок")

    print("\n=== нажимаем её ===")
    await hr.grant_name(upd, ctx, role_id, name)
    grants = await db.get_role_grants(role_id)
    print(" ", grants)
    assert len(grants) == 1 and grants[0]["name"] == name
    assert not grants[0]["cidr"], "адрес запоминать нельзя — он устареет"
    print("сохранено имя, а не цифры: ок")

    print("\n=== в раскладку уходит адрес имени ===")
    await db.add_user_role("rn-1", role_id)
    ok, msg = await acl.apply_access_rules("тест")
    assert ok, msg
    payload = sent["acl"]
    print(" ", json.dumps(payload, ensure_ascii=False))
    allow = payload["peers"][0]["allow"]
    assert allow[0]["cidr"] == "10.13.13.21/32", allow
    print("имя разрешилось в адрес того, кому принадлежит: ок")

    print("\n=== адрес сменился — правило переехало само ===")
    async def ips2():
        return {"rn-1": "10.13.13.20", "rn-2": "10.13.13.99"}
    acl.peer_ip_map = ips2
    await acl.apply_access_rules("смена адреса")
    allow = sent["acl"]["peers"][0]["allow"]
    print(" ", allow[0]["cidr"])
    assert allow[0]["cidr"] == "10.13.13.99/32", allow
    print("правило означает по-прежнему домашний сервер: ок")

    print("\n=== имя без адреса не открывает доступ молча ===")
    async def ips3():
        return {"rn-1": "10.13.13.20"}
    acl.peer_ip_map = ips3
    ok, msg = await acl.apply_access_rules("сервер исчез")
    print(" ", msg)
    assert ok and "не разрешились имена" in msg, msg
    assert sent["acl"]["peers"][0]["allow"] == [], sent["acl"]
    print("доступ не открыт, и об этом сказано: ок")

    print("\n=== разбор введённого руками ===")
    g, err = hr.parse_grant("дом.vpn tcp 8096")
    assert not err and g["name"] == "дом.vpn" and g["port"] == 8096, (g, err)
    g, err = hr.parse_grant("10.13.13.7 tcp 22")
    # Разбор нормализует одиночный адрес в /32 — так его и увидит узел.
    assert not err and g["cidr"] == "10.13.13.7/32" and not g.get("name"), (g, err)
    g, err = hr.parse_grant("192.168.1.5")
    assert err and "вне туннеля" in err, err
    print("имя, адрес и чужая сеть различаются: ок")

    print("\n=== как правило выглядит человеку ===")
    line = acl.grant_text({"name": "дом.vpn", "cidr": None, "proto": "tcp", "port": 8096})
    print(" ", line)
    assert line == "дом.vpn · tcp 8096", line
    print("показывается имя, а не подставленные цифры: ок")

    print("\n=== служебное имя удаляется насовсем ===")
    await db.execute("DELETE FROM settings WHERE key LIKE 'dns_node_name%'")
    await db.delete_dns_name(dn.NODE_NAME)
    assert await dn.ensure_node_name(), "не завелось при первом запуске"
    assert await db.get_dns_name(dn.NODE_NAME)
    await db.delete_dns_name(dn.NODE_NAME)
    await dn.apply_names("после удаления")
    assert await db.get_dns_name(dn.NODE_NAME) is None, \
        "имя вернулось само — владелец удалял его не для этого"
    print("удалили — не вернулось: ок")

    # Payload кладём на диск: узловой тест применит именно его.
    acl.peer_ip_map = ips
    await acl.apply_access_rules("для узлового теста")
    if os.path.isdir(os.path.dirname(PAYLOAD_OUT)):
        with open(PAYLOAD_OUT, "w", encoding="utf-8") as f:
            json.dump(sent["acl"], f, ensure_ascii=False)
        print("\nраскладка сохранена для узлового теста:", PAYLOAD_OUT)

    await db.execute("DELETE FROM users WHERE uuid LIKE 'rn-%'")
    await db.execute("DELETE FROM roles WHERE name LIKE 'тест-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
