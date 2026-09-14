# -*- coding: utf-8 -*-
"""Отказ роли: явный отлуп вместо таймаута и заворот веба на страницу."""
import ast
import io
import json
import os
import subprocess
import time

SRC = "/app/api.py"
NEED = {"_hook_after_accounting", "_acl_ensure_chain", "_acl_rule_spec", "apply_acl", "save_acl_state",
        "rebuild_acl", "_acl_web_ensure_chain", "apply_acl_web"}
CONSTS = {"ACL_CHAIN", "ACL_STATE_FILE", "TUNNEL_NET", "DE_AGENT_IP", "VPN_SUBNET",
          "CONF_DIR", "ACL_WEB_CHAIN", "ACL_WEB_PORTS", "BLOCK_PAGE_IP"}

tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEED:
        picked.append(node)
    elif isinstance(node, ast.Assign):
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & CONSTS:
            picked.append(node)

ns = {"subprocess": subprocess, "os": os, "json": json, "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
os.makedirs(ns["CONF_DIR"], exist_ok=True)

peers = [{"ip": "10.13.13.2", "allow": [{"cidr": "10.13.13.5/32", "proto": "any", "port": None}]}]
ns["apply_acl"](peers)
ns["apply_acl_web"](peers)


def chain(table, name):
    cmd = f"iptables {'-t ' + table if table else ''} -S {name}"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.splitlines()


acl = chain("", ns["ACL_CHAIN"])
print("цепочка доступов:")
for r in acl:
    print("   ", r)

assert not any("-j DROP" in r for r in acl), "молчаливый DROP остался — будет таймаут"
assert any("tcp-reset" in r for r in acl), "для TCP ожидается мгновенный отказ"
assert any("icmp-port-unreachable" in r for r in acl), "для остального — отказ ICMP"
print("\nотказ мгновенный, а не таймаут: ок")

tcp_i = next(i for i, r in enumerate(acl) if "tcp-reset" in r)
allow_i = max(i for i, r in enumerate(acl) if "10.13.13.5/32" in r)
assert allow_i < tcp_i, "разрешение должно стоять выше отказа"
print("разрешения выше отказа: ок")

web = chain("nat", ns["ACL_WEB_CHAIN"])
print("\nвеб-цепочка:")
for r in web:
    print("   ", r)

allow_w = [i for i, r in enumerate(web) if "10.13.13.5/32" in r and "RETURN" in r]
dnat_w = [i for i, r in enumerate(web) if "DNAT" in r]
assert allow_w and dnat_w, web
assert max(allow_w) < min(dnat_w), \
    "разрешённый сервис нельзя уводить на страницу отказа"
print("\nразрешённый сервис не уводится на страницу: ок")

for port, target in ns["ACL_WEB_PORTS"].items():
    assert any(f"--dport {port} " in r and f"{ns['BLOCK_PAGE_IP']}:{target}" in r
               for r in web), f"нет порта {port} → {target}"
# HTTPS обязан попадать на слушатель с сертификатом, а не на обычный HTTP.
# Порт 8443, а не 443: сам 443 на узле занят входом Xray.
assert any("--dport 443 " in r and ":8443" in r for r in web), \
    "HTTPS должен уходить на слушатель с сертификатом, а не на обычный HTTP"
print("веб-порты уводятся на страницу отказа, 443 — на TLS (8443): ок")

pre = subprocess.run("iptables -t nat -S PREROUTING", shell=True,
                     capture_output=True, text=True).stdout
# Привязки к интерфейсу тут нет намеренно: во время переезда пиры живут и на
# wg0, и на wg1, а адрес назначения из туннельной сети однозначно говорит, что
# это свои. Правило, привязанное к одному интерфейсу, отвалилось бы на половине.
assert ns["ACL_WEB_CHAIN"] in pre and "10.13.13.0/24" in pre, pre
assert "-i wg0" not in pre, "привязка к одному интерфейсу сломает переезд"
print("веб-цепочка висит на туннельных адресах, без привязки к интерфейсу: ок")

ns["apply_acl"](peers); ns["apply_acl_web"](peers)
ns["apply_acl"](peers); ns["apply_acl_web"](peers)
hooks = [l for l in subprocess.run("iptables -t nat -S PREROUTING", shell=True,
                                   capture_output=True, text=True).stdout.splitlines()
         if ns["ACL_WEB_CHAIN"] in l]
assert len(hooks) == 1, hooks
assert len(chain("nat", ns["ACL_WEB_CHAIN"])) == len(web), "правила задвоились"
print("повторное применение идемпотентно: ок")

ns["apply_acl"]([]); ns["apply_acl_web"]([])
assert not [r for r in chain("nat", ns["ACL_WEB_CHAIN"]) if "DNAT" in r]
assert not [r for r in chain("", ns["ACL_CHAIN"]) if "REJECT" in r]
print("снятие ролей убирает и отказы, и заворот: ок")

print("\nВСЁ ПРОШЛО")
