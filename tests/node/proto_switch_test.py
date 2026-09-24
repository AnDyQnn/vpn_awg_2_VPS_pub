# -*- coding: utf-8 -*-
"""Выключатель протоколов не гасит единственный вход.

После того как свой Xray убран, вход у узла один — AmneziaWG. Погасить его
значит оставить узел без связи, а вернуть можно будет только руками по SSH.

Проверяется:
  • выключить AmneziaWG нельзя — узел отказывает;
  • второго протокола узел не знает;
  • старый файл состояния, где записан ключ `xray`, читается без ошибок и
    ничего не включает;
  • в панели узла не осталось точек `/api/xray/*`.
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
text = io.open(SRC, encoding="utf-8").read()
tree = ast.parse(text)
picked = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        continue
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        continue
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.decorator_list = []
    picked.append(node)


class HTTPErr(Exception):
    pass


ns = {"subprocess": subprocess, "os": os, "json": json, "time": time, "re": re,
      "ipaddress": __import__("ipaddress"), "uuid": __import__("uuid"),
      "urllib": __import__("urllib.request"),
      "HTTPException": lambda status_code=500, detail="": HTTPErr(detail),
      "BaseModel": type("BaseModel", (), {}),
      "List": typing.List, "Optional": typing.Optional,
      "Depends": lambda *a, **k: None, "Request": object,
      "FastAPI": lambda *a, **k: type("App", (), {
          "post": lambda self, *a, **k: (lambda f: f),
          "get": lambda self, *a, **k: (lambda f: f),
          "delete": lambda self, *a, **k: (lambda f: f)})()}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
os.makedirs(ns["CONF_DIR"], exist_ok=True)

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Req:
    def __init__(self, name, enabled):
        self.name, self.enabled = name, enabled


# Подъём интерфейса в тесте не нужен — проверяем решение, а не сеть.
ns["awg_up"] = lambda: None

print("=== выключить AmneziaWG нельзя ===")
try:
    ns["api_protocols"](Req("awg", False))
    refused = False
except HTTPErr as e:
    refused = "единственный" in str(e)
check("узел отказал", refused)

print()
print("=== включить можно — это подъём интерфейса ===")
res = ns["api_protocols"](Req("awg", True))
check("ответ ok", res.get("status") == "ok", str(res))

print()
print("=== второго протокола узел не знает ===")
try:
    ns["api_protocols"](Req("xray", True))
    known = True
except HTTPErr:
    known = False
check("xray — неизвестный протокол", not known)

print()
print("=== старый файл состояния ===")
with open(ns["PROTO_STATE"], "w") as f:
    json.dump({"awg": True, "xray": True}, f)
st = ns["proto_state"]()
check("читается без ошибок", st == {"awg": True}, str(st))

print()
print("=== точек Xray в панели нет ===")
left = re.findall(r'@app\.\w+\("(/api/xray[^"]*)"', text)
check("ни одной /api/xray/*", not left, str(left))
check("статус AmneziaWG на своём адресе", '"/api/awg/status"' in text)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
