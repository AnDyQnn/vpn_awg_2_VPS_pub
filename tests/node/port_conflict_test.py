# -*- coding: utf-8 -*-
"""443 должен достаться Xray, страница отказа — уехать на 8443.

Проверка живая: поднимаем настоящий DNS-фильтр со страницей отказа, а затем
настоящий Xray с входом на 443. Если они снова подерутся за порт, второй
просто не встанет — и это увидит тест, а не человек, оставшийся без VPN.
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


def listening():
    out = sh("netstat -tlnp 2>/dev/null || ss -tlnp")
    return out


sh("ip link add tun0 type dummy")
sh("ip addr add 10.13.13.1/24 dev tun0")
sh("ip link set up dev tun0")

print("=== поднимаем страницу отказа ===")
page = subprocess.Popen("/opt/venv/bin/python3 -u /app/dnsfilter.py",
                        shell=True, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True)
time.sleep(4)
ports = listening()
print([l.split()[3] for l in ports.splitlines() if ":80 " in l or ":8443" in l or ":443 " in l])
assert ":8443" in ports, "страница отказа не поднялась на 8443"
assert ":443 " not in ports.replace(":8443", ""), "443 всё ещё занят страницей"
print("страница на 80 и 8443, 443 свободен: ок")

print("\n=== Xray занимает 443 ===")
CONFIG = {
    "log": {"loglevel": "warning"},
    "inbounds": [{"tag": "in", "listen": "0.0.0.0", "port": 443,
                  "protocol": "socks", "settings": {"auth": "noauth"}}],
    "outbounds": [{"protocol": "freedom", "tag": "direct"}],
}
ns["save_proto_state"]({"awg": True, "xray": True})
res = ns["xray_apply"](CONFIG, [])
print(res)
assert ns["xray_running"](), "Xray не поднялся — порт снова занят"
time.sleep(1)
assert ":443 " in listening(), "Xray не слушает 443"
print("Xray слушает 443: ок")

print("\n=== запрос человека к закрытому сервису уводится на страницу ===")
ns["apply_acl_web"]([{"ip": "10.13.13.50"}])
rules = sh("iptables -t nat -S WG_ACL_WEB")
print([r for r in rules.splitlines() if "443" in r])
assert "--dport 443 -j DNAT --to-destination 10.13.13.1:8443" in rules, rules
print("443 уводится на 8443, а не на занятый порт: ок")

ns["xray_stop"]()
page.terminate()
print("\nВСЁ ПРОШЛО")
