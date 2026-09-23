# -*- coding: utf-8 -*-
"""Проверка правил доступов на живом iptables внутри контейнера.

Функции берутся из настоящего api.py, а не переписываются: модуль целиком
импортировать нельзя (на импорте он поднимает сеть узла), поэтому из файла
достаются ровно нужные определения и выполняются как есть.
"""
import ast
import io
import json
import os
import subprocess
import time

SRC = "/app/api.py"
NEED_FUNCS = {"_hook_after_accounting", "_acl_ensure_chain", "_acl_rule_spec", "apply_acl",
              "save_acl_state", "rebuild_acl",
              "_acl_web_ensure_chain", "apply_acl_web"}
NEED_CONSTS = {"ACL_CHAIN", "ACL_STATE_FILE", "TUNNEL_NET", "DE_AGENT_IP", "NODE_IP",
               "VPN_SUBNET", "CONF_DIR", "ACL_WEB_CHAIN", "ACL_WEB_PORTS",
               "BLOCK_PAGE_IP"}

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
    return subprocess.run(f"iptables -S {ns['ACL_CHAIN']}", shell=True,
                          capture_output=True, text=True).stdout.strip().splitlines()


def forward():
    return subprocess.run("iptables -S FORWARD", shell=True,
                          capture_output=True, text=True).stdout.strip().splitlines()


# узел при старте вешает счётчики первыми — воспроизводим, чтобы проверить порядок
subprocess.run("iptables -N PEER_ACCT", shell=True, stderr=subprocess.DEVNULL)
subprocess.run("iptables -I FORWARD 1 -j PEER_ACCT", shell=True)

peers = [
    {"ip": "10.13.13.2", "allow": [
        {"cidr": "10.13.13.5/32", "proto": "any", "port": None},
        {"cidr": "10.13.13.6/32", "proto": "tcp", "port": 22},
    ]},
    {"ip": "10.13.13.3", "allow": []},          # роль без разрешений
]
rules = ns["apply_acl"](peers)
print("применено правил:", rules)

body = chain()
print("\nцепочка:")
for line in body:
    print("   ", line)

assert any("-d 10.13.13.254" in l and "RETURN" in l for l in body), \
    "путь в интернет через клиент-сервер обязан оставаться открытым"
assert body.index([l for l in body if "10.13.13.254" in l][0]) == 1, \
    "исключение для клиент-сервера должно стоять первым правилом"
assert any("ESTABLISHED" in l and "RETURN" in l for l in body), \
    "ответный трафик уже разрешённых сессий должен проходить"
assert any("-s 10.13.13.2/32 -d 10.13.13.5/32 -j RETURN" in l for l in body)
assert any("-s 10.13.13.2/32 -d 10.13.13.6/32 -p tcp -m tcp --dport 22 -j RETURN" in l
           for l in body), "правило с портом не встало"
# Запрет ЯВНЫЙ (REJECT), а не молчаливый DROP: отказ приходит мгновенно
# и читается как «закрыто», а не как «сломалось».
assert any("-s 10.13.13.2/32 -j REJECT" in l for l in body), "замыкающий запрет не встал"
assert any("-s 10.13.13.3/32 -j REJECT" in l for l in body), \
    "пустая роль обязана закрывать туннель целиком"
print("\nсодержимое цепочки: ок")

# --- узел должен быть доступен при любой роли -----------------------------
# Это ломалось по-настоящему: в профиле Xray наш резолвер прописан как DNS
# туннеля, а цепочка ролей висит и на OUTPUT — то есть пакеты человека на Xray
# к 10.13.13.1 попадали под замыкающий запрет его роли. Интернет по адресам
# работал, имена не разрешались: «подключается, но ничего не грузится».
node_idx = next((i for i, l in enumerate(body)
                 if "-d %s/32 -j RETURN" % ns["NODE_IP"] in l), None)
assert node_idx is not None, "узел не выведен из-под правил ролей"
for who in ("10.13.13.2", "10.13.13.3"):
    deny = next(i for i, l in enumerate(body) if "-s %s/32 -j REJECT" % who in l)
    assert node_idx < deny, "%s: запрет роли выше доступа к узлу" % who
print("резолвер и страница отказа доступны при любой роли: ок")

# А панель узла при этом обязана остаться закрытой. В INPUT её закрывает
# правило с «-i wg0», но запрос человека на Xray приходит к узлу по локальной
# петле и под то правило не попадает — значит закрывать надо здесь.
panel_idx = next((i for i, l in enumerate(body)
                  if "-d %s/32" % ns["NODE_IP"] in l and "--dport 8000" in l
                  and "REJECT" in l), None)
assert panel_idx is not None, "панель узла осталась открытой через Xray"
assert panel_idx < node_idx, "панель закрывается позже, чем разрешается узел"
print("панель узла закрыта раньше разрешения: ок")

# порядок разрешений и запрета внутри одного пира
allow_idx = max(i for i, l in enumerate(body)
                if "-s 10.13.13.2/32" in l and "RETURN" in l)
drop_idx = next(i for i, l in enumerate(body) if "-s 10.13.13.2/32 -j REJECT" in l)
assert allow_idx < drop_idx, "запрет оказался выше разрешений — доступ бы не работал"
print("разрешения стоят выше запрета: ок")

fwd = forward()
print("\nFORWARD:")
for line in fwd:
    print("   ", line)
hook = [l for l in fwd if "WG_ACL" in l]
assert hook, "цепочка не подключена к FORWARD"
assert "-d 10.13.13.0/24" in hook[0], \
    "цепочка обязана ловить только адреса туннеля, иначе заденет интернет"
# Привязки к интерфейсу тут быть НЕ должно: люди на Xray приходят не с wg0.
# Адрес назначения из туннельной сети — признак надёжнее.
assert "-i wg0" not in hook[0], "привязка к интерфейсу потеряет людей на Xray"

out_hooks = subprocess.run("iptables -S OUTPUT", shell=True,
                           capture_output=True, text=True).stdout
assert "WG_ACL" in out_hooks, \
    "без второй точки роли не действуют на людей, подключённых по Xray"
print("цепочка висит и на транзите, и на трафике самого узла: ок")
assert fwd.index(hook[0]) > fwd.index([l for l in fwd if "PEER_ACCT" in l][0]), \
    "учёт пакетов должен идти до запрета — иначе дропнутое не посчитается"
print("\nподключение к FORWARD и порядок: ок")

# повторное применение не должно плодить хуки
ns["apply_acl"](peers)
ns["apply_acl"](peers)
assert len([l for l in forward() if "WG_ACL" in l]) == 1, "хук размножился"
assert len(chain()) == len(body), "правила задвоились"
print("повторное применение идемпотентно: ок")

# сохранение и восстановление после перезапуска контейнера
os.makedirs(ns["CONF_DIR"], exist_ok=True)
ns["save_acl_state"](peers)
subprocess.run(f"iptables -F {ns['ACL_CHAIN']}", shell=True)
assert not chain()[1:], "цепочка не очистилась"
ns["rebuild_acl"]()
assert len(chain()) == len(body), "после перезапуска правила не восстановились"
print("восстановление с диска после рестарта: ок")

# пустой список = снятие всех ограничений
ns["apply_acl"]([])
assert not [l for l in chain() if "DROP" in l], "ограничения должны сниматься целиком"
print("снятие всех ролей очищает правила: ок")

print("\nВСЁ ПРОШЛО")
