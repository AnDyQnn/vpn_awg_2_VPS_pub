# -*- coding: utf-8 -*-
"""Заворот 53-го порта: правила на живом iptables. В прод не уезжает."""
import ast
import io
import json
import os
import subprocess
import time

SRC = "/app/api.py"
NEED = {"_dns_ensure_chain", "apply_dns_filters", "save_dns_state",
        "read_dns_full_state", "ensure_block_page_reachable",
        "rebuild_dns_chain", "read_dns_clients", "read_dns_names", "apply_dns_names",
        "read_dns_state", "rebuild_dns_filters", "refresh_dns_lists"}
CONSTS = {"DNS_CHAIN", "DNS_STATE_FILE", "DNS_LOCAL_IP", "CONF_DIR",
          "DNS_NAMES_FILE", "VPN_SUBNET",
          # Адрес страницы отказа: на него заворачивается 443, иначе запрос
          # уходит во вход Xray.
          "BLOCK_PAGE_IP"}

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


def chain():
    return subprocess.run(f"iptables -t nat -S {ns['DNS_CHAIN']}", shell=True,
                          capture_output=True, text=True).stdout.strip().splitlines()


clients = {"10.13.13.2": ["ads"], "10.13.13.3": ["ads", "adult"], "10.13.13.4": []}
count = ns["apply_dns_filters"](clients)
print("под фильтром:", count)
assert count == 2, "пустой список категорий — это отсутствие фильтров"

rules = chain()
print("\nцепочка:")
for r in rules:
    print("   ", r)

for ip in ("10.13.13.2", "10.13.13.3"):
    for proto in ("udp", "tcp"):
        assert any(f"-s {ip}/32" in r and f"-p {proto}" in r and "DNAT" in r for r in rules), \
            f"нет правила для {ip}/{proto}"
assert not any("10.13.13.4" in r for r in rules), \
    "у кого категорий нет — тому заворот не нужен"
print("\nправила для обоих протоколов и только для нужных: ок")

assert all("10.13.13.1:53" in r for r in rules if "DNAT" in r), \
    "заворот должен вести на сам узел"
print("заворот ведёт на узел: ок")

fwd = subprocess.run("iptables -t nat -S PREROUTING", shell=True,
                     capture_output=True, text=True).stdout
assert "DNS_REDIR" in fwd and "-i wg0" in fwd, fwd
print("цепочка подключена к PREROUTING только на wg0: ок")

ns["apply_dns_filters"](clients)
ns["apply_dns_filters"](clients)
hooks = [l for l in subprocess.run("iptables -t nat -S PREROUTING", shell=True,
                                   capture_output=True, text=True).stdout.splitlines()
         if "DNS_REDIR" in l]
assert len(hooks) == 1, f"хук размножился: {hooks}"
assert len(chain()) == len(rules), "правила задвоились"
print("повторное применение идемпотентно: ок")

ns["save_dns_state"](clients)
assert ns["read_dns_state"]() == clients
subprocess.run(f"iptables -t nat -F {ns['DNS_CHAIN']}", shell=True)
assert len(chain()) == 1
ns["rebuild_dns_filters"]()
assert len(chain()) == len(rules), "после перезапуска заворот не восстановился"
print("состояние сохраняется и восстанавливается после рестарта: ок")

ns["apply_dns_filters"]({})
assert not [r for r in chain() if "DNAT" in r], "снятие фильтров должно убирать заворот"
print("снятие всех фильтров убирает заворот: ок")

print("\n=== страница отказа достижима по HTTPS ===")
# Резолвер отвечает адресом узла. По 80 браузер попадает на страницу, а
# 443 на узле занят входом Xray: без заворота человек получает ошибку
# сертификата вместо объяснения, почему сайт закрыт.
ns["ensure_block_page_reachable"]()
nat = subprocess.run("iptables -t nat -S", shell=True,
                     capture_output=True, text=True).stdout
redirects = [l for l in nat.splitlines()
             if "--dport 443" in l and "8443" in l]
assert redirects, "заворот 443 на страницу отказа не встал"
print("  заворотов:", len(redirects))

# Повторный вызов не должен плодить правила: он идёт при каждой
# раскладке фильтров.
ns["ensure_block_page_reachable"]()
nat2 = subprocess.run("iptables -t nat -S", shell=True,
                      capture_output=True, text=True).stdout
again = [l for l in nat2.splitlines()
         if "--dport 443" in l and "8443" in l]
assert len(again) == len(redirects), "правило задвоилось при повторе"
print("повтор не плодит правил: ок")

print("\nВСЁ ПРОШЛО")
