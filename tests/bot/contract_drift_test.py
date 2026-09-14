# -*- coding: utf-8 -*-
"""Ловит ли сверка расхождение — или всегда говорит «всё хорошо».

Проверка состояния, которая молчит при любой погоде, хуже, чем её отсутствие:
она создаёт уверенность вместо сведений. Поэтому здесь не «сверка отработала»,
а «сверка увидела ровно то, что мы сломали».

Узел не поднимаем — подменяем его ответы. Проверяется именно сравнение, а не
сеть: сеть проверяется отдельно, на стенде из двух контейнеров.
"""
import asyncio
import importlib.util
import sys

sys.path.insert(0, "/app")
from database import db                                   # noqa: E402

spec = importlib.util.spec_from_file_location(
    "node_contract", "/app/node_contract.py")
nc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nc)

ok = True


def expect(title, want_status, want_in_msg=""):
    """Гоняем сверку и смотрим, что она сказала про нужную строку."""
    global ok
    nc.LINES = []
    asyncio.get_event_loop().run_until_complete(nc.main())
    hit = [l for l in nc.LINES if title in l]
    good = bool(hit) and hit[0].split("|")[0] == want_status \
        and want_in_msg in hit[0]
    ok = ok and good
    print("  %s %-40s %s" % ("•" if good else "ПРОВАЛ:", title,
                             hit[0] if hit else "строки нет вовсе"))


NODE = {}


def fake_get(path):
    if path not in NODE:
        raise RuntimeError("узел не отвечает на " + path)
    return NODE[path]


nc.node_get = fake_get


def node_state(peers=(), names=None, acct=None, xray=None, acl=None):
    NODE.clear()
    NODE["/peers"] = list(peers)
    NODE["/dns/names"] = {"names": names or {}}
    NODE["/accounting"] = {"ts": 0, "peers": acct if acct is not None else {}}
    NODE["/xray/status"] = {"xray": xray or {"enabled": False, "up": False,
                                             "has_config": False}}
    NODE["/acl"] = acl or {"saved_at": "2026-09-14", "peers": [], "chain": ""}


# Тесты гоняются в одной базе и по алфавиту. Сверке нужно видеть ровно свой
# набор людей, поэтому таблицы приходится опустошать — но вернуть их обязаны:
# иначе всё, что идёт следом, получит пустую базу с двумя выдуманными людьми.
SAVED = {}


async def seed():
    await db.connect()
    for table in ("users", "xray_users", "dns_names"):
        SAVED[table] = await db.fetch_all("SELECT * FROM %s" % table)
    await db.execute("DELETE FROM xray_users")
    await db.execute("DELETE FROM dns_names")
    await db.execute("DELETE FROM users")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES "
        "('Аня','uuid-a',TRUE), ('Боря','uuid-b',TRUE)")


async def restore():
    """Возвращаем как было. Порядок обратный: сначала то, что ссылается."""
    await db.execute("DELETE FROM xray_users")
    await db.execute("DELETE FROM dns_names")
    await db.execute("DELETE FROM users")
    for table in ("users", "xray_users", "dns_names"):
        for row in SAVED.get(table) or []:
            cols = list(row.keys())
            marks = ", ".join("$%d" % (i + 1) for i in range(len(cols)))
            await db.execute(
                "INSERT INTO %s (%s) VALUES (%s)" % (table, ", ".join(cols), marks),
                *[row[c] for c in cols])


asyncio.get_event_loop().run_until_complete(seed())

print("=== всё сходится — сверка молчит ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}})
expect("Пиры: база против узла", "ok", "2, совпадают")

print()
print("=== человек есть в базе, но пропал с узла ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"}],
           acct={"10.13.13.2": {}})
expect("Пиры: база против узла", "error", "Боря")

print()
print("=== на узле лишний доступ, которого нет в базе ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"},
                  {"uuid": "чужой", "allowed_ips": "10.13.13.9/32"}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}, "10.13.13.9": {}})
expect("Пиры: база против узла", "error", "без владельца")

print()
print("=== адрес живёт, а счётчика на него нет ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"}],
           acct={"10.13.13.2": {}})
expect("Учёт трафика по адресам", "error", "10.13.13.3")


async def add_xray():
    await db.execute(
        "INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
        "VALUES ('uuid-a','x-1','tok-1')")


asyncio.get_event_loop().run_until_complete(add_xray())

print()
print("=== ключи Xray выданы, а на узле конфига нет ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}})
expect("Xray: ключи и узел", "error", "конфига на узле нет")

print()
print("=== конфиг есть, но процесс не работает ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}},
           xray={"has_config": True, "up": False})
expect("Xray: ключи и узел", "error", "процесс не работает")


async def add_name():
    await db.execute(
        "INSERT INTO dns_names (name, target_uuid) VALUES ('дом', 'uuid-a')")


asyncio.get_event_loop().run_until_complete(add_name())

print()
print("=== имя заведено, но на узел не разложено ===")
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}},
           xray={"has_config": True, "up": True})
expect("Имена внутри туннеля", "error", "дом")

print()
print("=== выходной узел: маршрут по умолчанию вместо адреса ===")
# Та самая раскладка с боевого мастера. Раньше здесь получалось две ложные
# тревоги сразу: «адрес 0.0.0.0 без счётчика» и «пира Германии нет на узле».
node_state(peers=[{"uuid": "uuid-a", "allowed_ips": "10.13.13.2/32"},
                  {"uuid": "uuid-b", "allowed_ips": "10.13.13.3/32"},
                  {"uuid": "DE_AGENT", "allowed_ips": "0.0.0.0/0",
                   "latest_handshake": int(__import__("time").time()) - 58}],
           acct={"10.13.13.2": {}, "10.13.13.3": {}},
           xray={"has_config": True, "up": True})
NODE["/health"] = {"status": "ok"}
NODE["/host/deploy_status"] = {"ts": 1, "hash": "abcdef1"}
nc.de_get = lambda path: NODE[path]
expect("Учёт трафика по адресам", "ok", "2 адресов")
expect("Туннель до Германии", "ok", "рукопожатие")

print()
print("=== узел не отвечает вовсе ===")
NODE.clear()
expect("Пиры: база против узла", "error", "не удалось сверить")

asyncio.get_event_loop().run_until_complete(restore())

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
