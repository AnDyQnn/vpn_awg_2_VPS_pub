# -*- coding: utf-8 -*-
"""Xray на живом файрволе: адрес-двойник, учёт трафика и роли.

Это главная проверка всей затеи. Если она проходит, то переход на Xray не
требует переписывать ни учёт, ни лимиты, ни роли, ни фильтры — они опознают
человека по адресу источника, а адрес у него есть и на новом протоколе.

Стенд повторяет узел: туннельная сеть на служебном интерфейсе, «интернет»
отдельным адресом, настоящий Xray и настоящие правила из api.py.
"""
import ast
import io
import json
import os
import re
import subprocess
import time
import typing

SRC = "/app/api.py"
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        continue
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        continue
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.decorator_list = []
    picked.append(node)

ns = {"subprocess": subprocess, "os": os, "json": json, "time": time, "re": re,
      "ipaddress": __import__("ipaddress"), "uuid": __import__("uuid"),
      "urllib": __import__("urllib.request"),
      "HTTPException": lambda status_code=500, detail="": Exception(detail),
      "BaseModel": type("BaseModel", (), {}),
      "List": typing.List, "Optional": typing.Optional,
      "Depends": lambda *a, **k: None, "Request": object,
      "FastAPI": lambda *a, **k: type("App", (), {
          "post": lambda self, *a, **k: (lambda f: f),
          "get": lambda self, *a, **k: (lambda f: f),
          "delete": lambda self, *a, **k: (lambda f: f)})()}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
os.makedirs(ns["CONF_DIR"], exist_ok=True)


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def reachable(port, url, timeout=5):
    """Прошёл ли запрос через Xray конкретного человека."""
    r = subprocess.run(f"curl -s -o /dev/null --max-time {timeout} "
                       f"--socks5 127.0.0.1:{port} {url}",
                       shell=True, capture_output=True, text=True)
    return r.returncode == 0


# --- стенд ----------------------------------------------------------------
# Туннель: адрес узла .1, за ним — сеть пиров. Их адреса узлу НЕ принадлежат.
sh("ip link add tun0 type dummy")
sh("ip addr add 10.13.13.1/24 dev tun0")
sh("ip link set up dev tun0")

# «Домашний сервис» одного из пиров — то, что закрывают роли.
sh("ip link add home type dummy")
sh("ip addr add 10.13.13.5/32 dev home")
sh("ip link set up dev home")

# «Интернет»
sh("ip link add net0 type dummy")
sh("ip addr add 10.99.0.1/32 dev net0")
sh("ip link set up dev net0")

subprocess.Popen("python3 -m http.server 8080 --bind 10.99.0.1",
                 shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.Popen("python3 -m http.server 80 --bind 10.13.13.5",
                 shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

FIRST, SECOND = "10.13.13.134", "10.13.13.135"      # двойники пиров .6 и .7

CONFIG = {
    "log": {"loglevel": "warning"},
    "inbounds": [
        {"port": 1081, "listen": "127.0.0.1", "protocol": "socks",
         "tag": "in-first", "settings": {"auth": "noauth"}},
        {"port": 1082, "listen": "127.0.0.1", "protocol": "socks",
         "tag": "in-second", "settings": {"auth": "noauth"}},
    ],
    "outbounds": [
        {"protocol": "freedom", "tag": "out-first", "sendThrough": FIRST},
        {"protocol": "freedom", "tag": "out-second", "sendThrough": SECOND},
    ],
    "routing": {"rules": [
        {"type": "field", "inboundTag": ["in-first"], "outboundTag": "out-first"},
        {"type": "field", "inboundTag": ["in-second"], "outboundTag": "out-second"},
    ]},
}

print("=== узел поднимает адреса людей у себя ===")
ns["save_proto_state"]({"awg": True, "xray": True})
res = ns["xray_apply"](CONFIG, [FIRST, SECOND])
print(res)
up = ns["xray_addresses"]()
print("адреса на служебном интерфейсе:", sorted(up))
assert up == {FIRST, SECOND}, up
assert ns["xray_running"](), "процесс не поднялся"
print("оба адреса подняты, Xray работает: ок")

print("\n=== трафик человека реально ходит ===")
assert reachable(1081, "http://10.99.0.1:8080/"), \
    "запрос не прошёл — значит адрес-двойник не работает"
assert reachable(1082, "http://10.99.0.1:8080/")
print("оба вышли в «интернет»: ок")

print("\n=== счётчики видят каждого отдельно ===")
stats = ns["read_accounting"]()
print({ip: v["tx_packets"] for ip, v in stats.items() if ip in (FIRST, SECOND)})
assert stats.get(FIRST, {}).get("tx_packets", 0) > 0, "трафик первого не посчитан"
assert stats.get(SECOND, {}).get("tx_packets", 0) > 0, "трафик второго не посчитан"
print("учёт по адресам работает — лимиты и графики переносятся: ок")

print("\n=== до роли домашний сервис открыт обоим ===")
assert reachable(1081, "http://10.13.13.5/"), "сервис недоступен ещё до ролей"
assert reachable(1082, "http://10.13.13.5/")
print("оба дошли: ок")

print("\n=== роль закрывает туннель первому ===")
# Роль без разрешений = «внутрь туннеля нельзя ничего».
applied = ns["apply_acl"]([{"ip": FIRST, "allow": []}])
print("правил применено:", applied)
t0 = time.time()
blocked = not reachable(1081, "http://10.13.13.5/", timeout=8)
took = time.time() - t0
assert blocked, "роль не подействовала на человека, подключённого по Xray"
print(f"первому закрыто, отказ за {took:.1f} с (не таймаут): ок")
assert took < 5, "похоже на молчаливый DROP, а человек должен получать отказ сразу"

print("\n=== второму ничего не закрывали ===")
assert reachable(1082, "http://10.13.13.5/"), "задело человека без роли"
print("ходит как раньше: ок")

print("\n=== интернет роль не трогает ===")
assert reachable(1081, "http://10.99.0.1:8080/"), \
    "роль отрезала интернет — она должна закрывать только туннель"
print("интернет у закрытого человека остался: ок")

print("\n=== разрешение в роли открывает именно то, что указано ===")
ns["apply_acl"]([{"ip": FIRST, "allow": [
    {"cidr": "10.13.13.5/32", "proto": "tcp", "port": 80}]}])
assert reachable(1081, "http://10.13.13.5/"), "разрешение не сработало"
print("открыли — дошёл: ок")

print("\n=== адрес ушедшего человека снимается ===")
ns["xray_sync_addresses"]([FIRST])
up = ns["xray_addresses"]()
print("осталось:", sorted(up))
assert up == {FIRST}, up
after = ns["read_accounting"]()
assert SECOND not in after, "счётчик снятого адреса остался — статистика поехала бы"
print("адрес и счётчик убраны вместе: ок")

ns["xray_stop"]()
print("\nВСЁ ПРОШЛО")
