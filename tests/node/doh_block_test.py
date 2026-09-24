# -*- coding: utf-8 -*-
"""Обход фильтра через чужой DNS закрыт.

Фильтр сайтов держится на том, что имена спрашивают у нас. Заворот на 53-м
порту это обеспечивал — но только для обычного DNS. А телефон и браузер по
умолчанию спрашивают иначе: «Приватный DNS» в Android и iOS это DNS поверх TLS
(порт 853), Chrome и Firefox — DNS поверх HTTPS (порт 443 к известным
резолверам). Оба пути шли мимо нас.

Со стороны это выглядело как «фильтры не работают», хотя фильтр был исправен:
на боевом узле запрещённое имя он отдавал страницей отказа. Его просто не
спрашивали.

Здесь проверяется, что обходные пути закрыты, и — не менее важно — что при этом
не задето лишнее: наш собственный резолвер и обычные сайты на 443.
"""
import ast
import io
import json
import os
import subprocess
import time

SRC = "/app/api.py"
NEED_FUNCS = {"doh_block_apply"}
NEED_CONSTS = {"DOH_CHAIN", "DOH_SET", "DOH_ADDRS", "TUNNEL_NET", "NODE_IP",
               "VPN_SUBNET", "CONF_DIR"}

tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEED_FUNCS:
        picked.append(node)
    elif isinstance(node, ast.Assign):
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & NEED_CONSTS:
            picked.append(node)
ns = {"subprocess": subprocess, "os": os, "json": json, "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
print("взято из api.py:", ", ".join(sorted(NEED_FUNCS)))


def chain():
    return subprocess.run(f"iptables -S {ns['DOH_CHAIN']}", shell=True,
                          capture_output=True, text=True).stdout.splitlines()


def hooks(name):
    out = subprocess.run(f"iptables -S {name}", shell=True,
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if ns["DOH_CHAIN"] in l]


print("\n=== включаем запрет ===")
count = ns["doh_block_apply"](True)
print("  правил:", count)
body = chain()
for line in body:
    print("   ", line)

print("\n=== закрыт DNS поверх TLS — это «Приватный DNS» в телефоне ===")
assert [l for l in body if "dpt:853" in l or "--dport 853" in l], \
    "порт 853 открыт — телефон будет спрашивать имена мимо нас"
print("  порт 853 закрыт: ок")

print("\n=== закрыт DNS поверх HTTPS у известных резолверов ===")
tcp443 = [l for l in body if "--dport 443" in l and "-p tcp" in l]
udp443 = [l for l in body if "--dport 443" in l and "-p udp" in l]
assert tcp443, "443 к известным резолверам открыт по TCP"
assert udp443, "443 к известным резолверам открыт по QUIC — а он тоже DNS возит"
assert all(ns["DOH_SET"] in l for l in tcp443 + udp443), (
    "443 закрыт не по списку резолверов, а целиком — это отрезало бы интернет")
print("  443 закрыт только к резолверам из списка, и по TCP, и по QUIC: ок")

print("\n=== отказ мгновенный, а не молчаливый ===")
# Молчание заставило бы приложение ждать таймаут, и человек увидел бы «интернет
# тупит». Мгновенный отказ возвращает его к обычному DNS, то есть к нам.
assert not [l for l in body if "-j DROP" in l], "молчаливый DROP — будет таймаут"
rules_only = [l for l in body if l.startswith("-A ")]
assert rules_only and all("REJECT" in l for l in rules_only), \
    "не все правила отвечают отказом"
print("  везде мгновенный отказ: ок")

print("\n=== исключений по адресам нет ===")
# Раньше первым стоял пропуск для адресов-двойников своего Xray. Xray убран —
# пропуск остался бы дырой: запрет не действовал бы на половину сети туннеля.
assert not [l for l in rules_only if "RETURN" in l], (
    "в запрете остался пропуск: " + str([l for l in rules_only if "RETURN" in l]))
print("  пропусков нет: ок")

print("\n=== наш собственный резолвер не задет ===")
own = [l for l in body if "--dport 53" in l]
assert own, "правило про чужой обычный DNS пропало"
assert all(f"! -d {ns['NODE_IP']}" in l for l in own), (
    "запрет на 53 не делает исключения для нашего адреса — "
    "люди остались бы вообще без имён")
print("  запрос к нашему адресу исключён: ок")

print("\n=== список резолверов заполнен и не пуст ===")
n = subprocess.run(f"ipset list {ns['DOH_SET']} 2>/dev/null | grep -c '^[0-9]'",
                   shell=True, capture_output=True, text=True).stdout.strip()
print("  адресов в списке:", n)
assert int(n or 0) >= 10, "список резолверов пуст — запрет ничего не ловит"

print("\n=== запрет висит и на транзите, и на трафике узла ===")
# Трафик, рождённый на самом узле, через транзит
# не проходит вовсе. Без второй точки запрет его не коснулся бы.
assert hooks("FORWARD"), "запрет не подключён к транзиту"
assert hooks("OUTPUT"), (
    "запрет не подключён к трафику узла")
for h in hooks("FORWARD") + hooks("OUTPUT"):
    assert f"-s {ns['TUNNEL_NET']}" in h, (
        "запрет ловит не только туннель — задело бы сам узел, "
        "и он остался бы без своего DNS наверх")
print("  обе точки, и только для туннеля: ок")

print("\n=== повторное применение ничего не плодит ===")
before = len(chain())
ns["doh_block_apply"](True)
ns["doh_block_apply"](True)
assert len(chain()) == before, "правила задвоились"
assert len(hooks("FORWARD")) == 1 and len(hooks("OUTPUT")) == 1, "хук размножился"
print("  идемпотентно: ок")

print("\n=== выключение снимает всё ===")
ns["doh_block_apply"](False)
assert not hooks("FORWARD") and not hooks("OUTPUT"), "запрет остался подключён"
print("  снято: ок")

print("\nВСЁ ПРОШЛО")
