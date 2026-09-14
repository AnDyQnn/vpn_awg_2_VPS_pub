# -*- coding: utf-8 -*-
"""Узел: таблица имён и заворот DNS туннеля на себя.

Заворот общий для всей туннельной сети — имя должно работать у всех. Но пока
имён нет ни одного, его быть не должно: поведение узла остаётся ровно таким,
каким было до появления этой возможности.
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


def chain():
    return subprocess.run(f"iptables -t nat -S {ns['DNS_CHAIN']}", shell=True,
                          capture_output=True, text=True).stdout


print("=== пока имён нет, ничего не заворачивается ===")
ns["apply_dns_names"]({})
body = chain()
print(body.strip() or "  (цепочка пуста)")
assert "10.13.13.0/24" not in body, "заворот появился на пустом месте"
print("узел ведёт себя как раньше: ок")

print("\n=== завели имя — DNS туннеля идёт на узел ===")
count = ns["apply_dns_names"]({"дом.vpn": "10.13.13.5", "panel.vpn": "10.13.13.1"})
print("  имён принято:", count)
body = chain()
for line in body.strip().splitlines():
    print("   ", line)
assert count == 2
assert body.count("--dport 53") == 2, "должно быть два правила: udp и tcp"
assert "10.13.13.0/24" in body and "10.13.13.1:53" in body
print("оба протокола заворачиваются на узел: ок")

print("\n=== таблица легла на диск для DNS-процесса ===")
saved = ns["read_dns_names"]()
print("  ", saved)
assert saved == {"дом.vpn": "10.13.13.5", "panel.vpn": "10.13.13.1"}, saved
print("имена на месте: ок")

print("\n=== повторное применение не плодит правила ===")
ns["apply_dns_names"]({"panel.vpn": "10.13.13.1"})
body = chain()
assert body.count("--dport 53") == 2, body
print("по-прежнему два: ок")

print("\n=== последнее имя удалили — заворот снят ===")
ns["apply_dns_names"]({})
body = chain()
print(body.strip() or "  (цепочка пуста)")
assert "10.13.13.0/24" not in body, "заворот остался без единого имени"
assert ns["read_dns_names"]() == {}
print("узел вернулся к прежнему поведению: ок")

print("\n=== фильтры и имена не мешают друг другу ===")
# Через те же точки входа, что и на бою: иначе проверяем не то, что работает.
ns["set_dns_filters"](type("R", (), {"clients": {"10.13.13.9": ["adult"]},
                                     "common": [], "custom": [],
                                     "bot_link": ""})())
ns["set_dns_names"](type("R", (), {"names": {"panel.vpn": "10.13.13.1"},
                                    "upstreams": {}})())
body = chain()
assert "-s 10.13.13.9/32" in body, "заворот для фильтруемого пропал"
assert "-s 10.13.13.0/24" in body, "заворот для имён не встал"
print("оба вида правил живут в одной цепочке: ок")

print("\nВСЁ ПРОШЛО")
