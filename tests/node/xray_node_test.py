# -*- coding: utf-8 -*-
"""Узловая часть Xray: процесс, конфиг, откат, выключатели протоколов."""
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


class Req:
    def __init__(self, **kw):
        self.__dict__.update(kw)


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

# Поднять настоящий wg0 в контейнере без NET_ADMIN нельзя, да и проверяем мы
# здесь не WireGuard, а выключатели. Подменяем — и заодно следим, что выключатель
# действительно дёргает интерфейс, а не только пишет состояние в файл.
awg_calls = []
ns["awg_up"] = lambda: awg_calls.append("up")
ns["awg_down"] = lambda: awg_calls.append("down")

GOOD = {
    "log": {"loglevel": "warning"},
    "inbounds": [{"port": 10800, "listen": "127.0.0.1", "protocol": "socks",
                  "tag": "in", "settings": {"auth": "noauth"}}],
    "outbounds": [{"protocol": "freedom", "tag": "out"}],
}
BROKEN = {"inbounds": [{"port": "это не порт", "protocol": "нет такого"}]}

print("=== состояние по умолчанию ===")
st = ns["proto_state"]()
print(st)
assert st == {"awg": True, "xray": False}, st
print("AmneziaWG включён, Xray выключен — как и было до обновления: ок")

print("\n=== ключи Reality ===")
keys = ns["api_xray_keys"]()
assert any("private" in k for k in keys) and any("public" in k for k in keys), keys
print("сгенерированы:", {k: v[:12] + "…" for k, v in keys.items()})

print("\n=== конфиг при выключенном протоколе ===")
res = ns["xray_apply"](GOOD)
print(res)
assert "выключен" in res["note"], res
assert not ns["xray_running"](), "процесс не должен подниматься, пока протокол выключен"
print("конфиг записан, процесс не поднят: ок")

print("\n=== включаем Xray ===")
res = ns["api_protocols"](Req(name="xray", enabled=True))
print(res)
assert res["state"]["xray"] and ns["xray_running"](), res
print("процесс поднялся: ок")

print("\n=== битый конфиг должен откатиться ===")
try:
    ns["xray_apply"](BROKEN)
    raise AssertionError("битый конфиг приняли — это потеря связи для всех")
except RuntimeError as e:
    print("отказ:", e)
saved = json.load(open(ns["XRAY_CONF"]))
assert saved == GOOD, "на диске остался битый конфиг"
assert ns["xray_running"](), "после отката процесс должен работать"
print("вернулся прежний конфиг, процесс живой: ок")

print("\n=== состояние для экрана ===")
status = ns["api_xray_status"]()
print(json.dumps(status, ensure_ascii=False))
assert status["xray"]["up"] and status["xray"]["enabled"] and status["xray"]["has_config"]
assert status["awg"]["enabled"]
print("статус собирается: ок")

print("\n=== выключить оба нельзя ===")
try:
    ns["api_protocols"](Req(name="awg", enabled=False))
    print("  AmneziaWG выключён (Xray работает) — это допустимо")
    st = ns["proto_state"]()
    assert st == {"awg": False, "xray": True}, st
    try:
        ns["api_protocols"](Req(name="xray", enabled=False))
        raise AssertionError("выключили оба — узел остался бы без входа")
    except Exception as e:
        assert "без входа" in str(e), e
        print("  попытка выключить второй отбита:", e)
except AssertionError:
    raise

print("\n=== выключаем Xray обратно ===")
ns["api_protocols"](Req(name="awg", enabled=True))
assert awg_calls == ["down", "up"], awg_calls
print("выключатель AmneziaWG гасил и поднимал интерфейс:", awg_calls)
res = ns["api_protocols"](Req(name="xray", enabled=False))
assert not ns["xray_running"](), "процесс должен остановиться"
print("остановлен, состояние:", ns["proto_state"]())

print("\nВСЁ ПРОШЛО")
